#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <stdio.h>
#include <string.h>

#ifdef _WIN32
#  define WIN32_LEAN_AND_MEAN
#  include <windows.h>
#  include <conio.h>
#else
#  include <errno.h>
#  include <termios.h>
#  include <unistd.h>
#  include <sys/select.h>
#endif

/* Key kind strings mirror Python xrk_readline.keys.Key */
#define KIND_ENTER "enter"
#define KIND_BACKSPACE "backspace"
#define KIND_DELETE "delete"
#define KIND_LEFT "left"
#define KIND_RIGHT "right"
#define KIND_UP "up"
#define KIND_DOWN "down"
#define KIND_HOME "home"
#define KIND_END "end"
#define KIND_TAB "tab"
#define KIND_CTRL_C "ctrl_c"
#define KIND_CTRL_D "ctrl_d"
#define KIND_CHAR "char"

#ifndef _WIN32
static struct termios g_old;
static int g_raw = 0;
#endif

#ifdef _WIN32
static int g_vt = 0;

static void
enable_vt(void)
{
    HANDLE h;
    DWORD mode;

    if (g_vt) {
        return;
    }
    h = GetStdHandle(STD_OUTPUT_HANDLE);
    if (h == INVALID_HANDLE_VALUE) {
        return;
    }
    if (!GetConsoleMode(h, &mode)) {
        return;
    }
    mode |= ENABLE_VIRTUAL_TERMINAL_PROCESSING;
    SetConsoleMode(h, mode);
    g_vt = 1;
}
#endif

static PyObject *
make_key(const char *kind, const char *ch)
{
    return Py_BuildValue("(ss)", kind, ch ? ch : "");
}

static PyObject *
xrk_backend(PyObject *self, PyObject *args)
{
    (void)self;
    (void)args;
    return PyUnicode_FromString("native-c");
}

static PyObject *
xrk_write(PyObject *self, PyObject *args)
{
    const char *text;
    Py_ssize_t n;

    (void)self;
    if (!PyArg_ParseTuple(args, "s#", &text, &n)) {
        return NULL;
    }
#ifdef _WIN32
    {
        HANDLE h = GetStdHandle(STD_OUTPUT_HANDLE);
        DWORD written = 0;
        if (h != INVALID_HANDLE_VALUE) {
            /* UTF-8 → wide → WriteConsoleW，避免 GBK 控制台乱码 */
            int wlen = MultiByteToWideChar(CP_UTF8, 0, text, (int)n, NULL, 0);
            if (wlen > 0) {
                wchar_t *wbuf = (wchar_t *)PyMem_Malloc((size_t)wlen * sizeof(wchar_t));
                if (!wbuf) {
                    return PyErr_NoMemory();
                }
                MultiByteToWideChar(CP_UTF8, 0, text, (int)n, wbuf, wlen);
                WriteConsoleW(h, wbuf, (DWORD)wlen, &written, NULL);
                PyMem_Free(wbuf);
                Py_RETURN_NONE;
            }
        }
    }
#endif
    if (fwrite(text, 1, (size_t)n, stdout) != (size_t)n) {
        return PyErr_SetFromErrno(PyExc_OSError);
    }
    Py_RETURN_NONE;
}

static PyObject *
xrk_flush(PyObject *self, PyObject *args)
{
    (void)self;
    (void)args;
    if (fflush(stdout) != 0) {
        return PyErr_SetFromErrno(PyExc_OSError);
    }
    Py_RETURN_NONE;
}

static PyObject *
xrk_enter_raw(PyObject *self, PyObject *args)
{
    (void)self;
    (void)args;
#ifdef _WIN32
    enable_vt();
    Py_RETURN_NONE;
#else
    if (!g_raw) {
        if (tcgetattr(STDIN_FILENO, &g_old) != 0) {
            return PyErr_SetFromErrno(PyExc_OSError);
        }
        {
            struct termios t = g_old;
            cfmakeraw(&t);
            t.c_lflag |= ISIG; /* 保留信号语义由我们读 \x03 处理 */
            t.c_cc[VMIN] = 0;
            t.c_cc[VTIME] = 0;
            if (tcsetattr(STDIN_FILENO, TCSANOW, &t) != 0) {
                return PyErr_SetFromErrno(PyExc_OSError);
            }
        }
        g_raw = 1;
    }
    Py_RETURN_NONE;
#endif
}

static PyObject *
xrk_leave_raw(PyObject *self, PyObject *args)
{
    (void)self;
    (void)args;
#ifndef _WIN32
    if (g_raw) {
        tcsetattr(STDIN_FILENO, TCSADRAIN, &g_old);
        g_raw = 0;
    }
#endif
    Py_RETURN_NONE;
}

#ifdef _WIN32
static int
poll_wch(int wait_ms)
{
    DWORD start = GetTickCount();
    for (;;) {
        if (_kbhit()) {
            return _getwch();
        }
        if (wait_ms >= 0) {
            DWORD elapsed = GetTickCount() - start;
            if ((int)elapsed >= (DWORD)wait_ms) {
                return -1;
            }
        }
        Sleep(5);
    }
}

static PyObject *
decode_ansi_win(void)
{
    int c1 = poll_wch(40);
    int c2;

    if (c1 < 0) {
        return make_key(KIND_CHAR, "");
    }
    if (c1 == '[') {
        c2 = poll_wch(40);
        if (c2 < 0) {
            return make_key(KIND_CHAR, "");
        }
        switch (c2) {
        case 'A': return make_key(KIND_UP, "");
        case 'B': return make_key(KIND_DOWN, "");
        case 'C': return make_key(KIND_RIGHT, "");
        case 'D': return make_key(KIND_LEFT, "");
        case 'H': return make_key(KIND_HOME, "");
        case 'F': return make_key(KIND_END, "");
        case '3':
            if (poll_wch(40) == '~') {
                return make_key(KIND_DELETE, "");
            }
            return make_key(KIND_CHAR, "");
        default: return make_key(KIND_CHAR, "");
        }
    }
    if (c1 == 'O') {
        c2 = poll_wch(40);
        if (c2 == 'H') return make_key(KIND_HOME, "");
        if (c2 == 'F') return make_key(KIND_END, "");
    }
    return make_key(KIND_CHAR, "");
}

static PyObject *
read_key_win(int timeout_ms)
{
    DWORD start = GetTickCount();

    enable_vt();
    for (;;) {
        if (_kbhit()) {
            int c = _getwch();
            if (c == 0 || c == 0xE0) {
                int c2 = _getwch();
                switch (c2) {
                case 72: return make_key(KIND_UP, "");
                case 80: return make_key(KIND_DOWN, "");
                case 75: return make_key(KIND_LEFT, "");
                case 77: return make_key(KIND_RIGHT, "");
                case 71: return make_key(KIND_HOME, "");
                case 79: return make_key(KIND_END, "");
                case 83: return make_key(KIND_DELETE, "");
                default: return make_key(KIND_CHAR, "");
                }
            }
            if (c == 27) {
                return decode_ansi_win();
            }
            if (c == '\r' || c == '\n') {
                return make_key(KIND_ENTER, "");
            }
            if (c == 8 || c == 127) {
                return make_key(KIND_BACKSPACE, "");
            }
            if (c == '\t') {
                return make_key(KIND_TAB, "");
            }
            if (c == 3) {
                return make_key(KIND_CTRL_C, "");
            }
            if (c == 4) {
                return make_key(KIND_CTRL_D, "");
            }
            if (c >= 32) {
                char utf8[8];
                wchar_t w = (wchar_t)c;
                int n = WideCharToMultiByte(CP_UTF8, 0, &w, 1, utf8, (int)sizeof(utf8) - 1, NULL, NULL);
                if (n <= 0) {
                    return make_key(KIND_CHAR, "");
                }
                utf8[n] = '\0';
                return make_key(KIND_CHAR, utf8);
            }
            return make_key(KIND_CHAR, "");
        }
        if (timeout_ms >= 0) {
            DWORD elapsed = GetTickCount() - start;
            if ((int)elapsed >= timeout_ms) {
                Py_RETURN_NONE;
            }
        }
        {
            int rc = Py_MakePendingCalls();
            if (rc < 0) {
                return NULL;
            }
        }
        Sleep(10);
    }
}
#else
static int
read_byte(int fd, char *out, int timeout_ms)
{
    fd_set rfds;
    struct timeval tv;
    int r;

    FD_ZERO(&rfds);
    FD_SET(fd, &rfds);
    if (timeout_ms < 0) {
        r = select(fd + 1, &rfds, NULL, NULL, NULL);
    } else {
        tv.tv_sec = timeout_ms / 1000;
        tv.tv_usec = (timeout_ms % 1000) * 1000;
        r = select(fd + 1, &rfds, NULL, NULL, &tv);
    }
    if (r < 0) {
        if (errno == EINTR) {
            return 0;
        }
        return -1;
    }
    if (r == 0) {
        return 0;
    }
    r = (int)read(fd, out, 1);
    if (r < 0) {
        return -1;
    }
    if (r == 0) {
        return 0;
    }
    return 1;
}

static PyObject *
decode_ansi(int fd)
{
    char buf[8];
    int n = 0;
    int i;

    for (i = 0; i < 6; i++) {
        char c;
        int got = read_byte(fd, &c, 25);
        if (got <= 0) {
            break;
        }
        buf[n++] = c;
    }
    buf[n] = '\0';
    if (n >= 2 && buf[0] == '[') {
        if (buf[1] == 'A') return make_key(KIND_UP, "");
        if (buf[1] == 'B') return make_key(KIND_DOWN, "");
        if (buf[1] == 'C') return make_key(KIND_RIGHT, "");
        if (buf[1] == 'D') return make_key(KIND_LEFT, "");
        if (buf[1] == 'H') return make_key(KIND_HOME, "");
        if (buf[1] == 'F') return make_key(KIND_END, "");
        if (n >= 3 && buf[1] == '3' && buf[2] == '~') return make_key(KIND_DELETE, "");
    }
    if (n >= 2 && buf[0] == 'O') {
        if (buf[1] == 'H') return make_key(KIND_HOME, "");
        if (buf[1] == 'F') return make_key(KIND_END, "");
    }
    return make_key(KIND_CHAR, "");
}

static PyObject *
read_key_posix(int timeout_ms)
{
    char ch;
    int got;
    int fd = STDIN_FILENO;
    char tmp[8];

    if (!g_raw) {
        PyObject *r = xrk_enter_raw(NULL, NULL);
        if (!r) {
            return NULL;
        }
        Py_DECREF(r);
    }

    got = read_byte(fd, &ch, timeout_ms < 0 ? 50 : timeout_ms);
    if (got < 0) {
        return PyErr_SetFromErrno(PyExc_OSError);
    }
    if (got == 0) {
        if (timeout_ms < 0) {
            /* 继续短轮询，让 Python 能跑 stop_check */
            Py_RETURN_NONE;
        }
        Py_RETURN_NONE;
    }

    if (ch == '\r' || ch == '\n') return make_key(KIND_ENTER, "");
    if (ch == 127 || ch == 8) return make_key(KIND_BACKSPACE, "");
    if (ch == '\t') return make_key(KIND_TAB, "");
    if (ch == 3) return make_key(KIND_CTRL_C, "");
    if (ch == 4) return make_key(KIND_CTRL_D, "");
    if (ch == 0x1b) return decode_ansi(fd);

    tmp[0] = ch;
    tmp[1] = '\0';
    /* 简易 UTF-8 续读 */
    if ((unsigned char)ch >= 0xC0) {
        int need = ((unsigned char)ch < 0xE0) ? 1 : ((unsigned char)ch < 0xF0) ? 2 : 3;
        int i;
        for (i = 0; i < need; i++) {
            char c2;
            int g2 = read_byte(fd, &c2, 30);
            if (g2 <= 0) {
                break;
            }
            tmp[i + 1] = c2;
            tmp[i + 2] = '\0';
        }
    }
    return make_key(KIND_CHAR, tmp);
}
#endif

static PyObject *
xrk_read_key(PyObject *self, PyObject *args)
{
    int timeout_ms = 50;

    (void)self;
    if (!PyArg_ParseTuple(args, "|i", &timeout_ms)) {
        return NULL;
    }
#ifdef _WIN32
    return read_key_win(timeout_ms);
#else
    return read_key_posix(timeout_ms);
#endif
}

static PyMethodDef methods[] = {
    {"backend", xrk_backend, METH_NOARGS, "Return backend id"},
    {"write", xrk_write, METH_VARARGS, "Write UTF-8 text to console"},
    {"flush", xrk_flush, METH_NOARGS, "Flush stdout"},
    {"enter_raw", xrk_enter_raw, METH_NOARGS, "Enter raw / enable VT"},
    {"leave_raw", xrk_leave_raw, METH_NOARGS, "Leave raw mode"},
    {"read_key", xrk_read_key, METH_VARARGS, "read_key(timeout_ms=50) -> (kind, ch)|None"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "xrk_readline._native",
    "xrk-readline native console backend (C)",
    -1,
    methods
};

PyMODINIT_FUNC
PyInit__native(void)
{
#ifdef _WIN32
    enable_vt();
#endif
    return PyModule_Create(&moduledef);
}
