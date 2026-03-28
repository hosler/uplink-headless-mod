/*
 * mikmodplayer — Python C extension for rendering .uni tracker files
 * via libmikmod. Returns raw PCM bytes for pygame Sound playback.
 *
 * Usage:
 *   import mikmodplayer
 *   pcm = mikmodplayer.render("/path/to/file.uni", seconds=120)
 *   # pcm is 44100Hz, 16-bit signed, stereo raw PCM
 */

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <mikmod.h>
#include <string.h>

static int g_initialized = 0;

static int ensure_init(void) {
    if (g_initialized) return 0;

    MikMod_RegisterDriver(&drv_nos);
    MikMod_RegisterAllLoaders();

    md_mixfreq = 44100;
    md_mode = DMODE_16BITS | DMODE_STEREO | DMODE_SOFT_MUSIC | DMODE_SOFT_SNDFX
              | DMODE_INTERP | DMODE_NOISEREDUCTION | DMODE_HQMIXER;

    if (MikMod_Init("")) {
        PyErr_Format(PyExc_RuntimeError, "MikMod_Init failed: %s",
                     MikMod_strerror(MikMod_errno));
        return -1;
    }

    g_initialized = 1;
    return 0;
}

static PyObject* mikmod_render(PyObject* self, PyObject* args, PyObject* kwargs) {
    const char* path;
    int seconds = 120;
    static char* kwlist[] = {"path", "seconds", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "s|i", kwlist, &path, &seconds))
        return NULL;

    if (ensure_init() != 0)
        return NULL;

    MODULE* module = Player_Load(path, 128, 0);
    if (!module) {
        PyErr_Format(PyExc_IOError, "Failed to load %s: %s",
                     path, MikMod_strerror(MikMod_errno));
        return NULL;
    }

    /* wrap=0 means don't loop — stop after playing once */
    module->wrap = 0;
    module->loop = 0;
    module->fadeout = 1;

    long buf_size = (long)44100 * 4 * seconds;
    char* buffer = (char*)malloc(buf_size);
    if (!buffer) {
        Player_Free(module);
        return PyErr_NoMemory();
    }

    Player_Start(module);

    /*
     * VC_WriteBytes is the core software mixer render function.
     * It advances the internal song position and writes PCM.
     * MikMod_Update() is only needed for the hardware driver path.
     * With drv_nos, VC_WriteBytes does all the work.
     *
     * Render in chunks matching the mixer's internal buffer expectations.
     * A larger chunk = fewer calls = smoother rendering.
     */
    long offset = 0;
    /* Render in 1-second chunks for steady progress */
    long chunk = 44100 * 4;  /* 1 second of 16-bit stereo */

    while (offset < buf_size && Player_Active()) {
        long to_write = chunk;
        if (offset + to_write > buf_size)
            to_write = buf_size - offset;

        ULONG written = VC_WriteBytes((SBYTE*)(buffer + offset), (ULONG)to_write);
        offset += written;

        /* Check if song has ended (wrapped back to start) */
        if (!Player_Active())
            break;
    }

    Player_Stop();
    Player_Free(module);

    /* Trim to actual rendered size */
    PyObject* result = PyBytes_FromStringAndSize(buffer, offset);
    free(buffer);
    return result;
}

static PyObject* mikmod_get_title(PyObject* self, PyObject* args) {
    const char* path;
    if (!PyArg_ParseTuple(args, "s", &path))
        return NULL;

    if (ensure_init() != 0)
        return NULL;

    char* title = Player_LoadTitle(path);
    if (title) {
        PyObject* result = PyUnicode_FromString(title);
        MikMod_free(title);
        return result;
    }
    Py_RETURN_NONE;
}

static PyMethodDef methods[] = {
    {"render", (PyCFunction)mikmod_render, METH_VARARGS | METH_KEYWORDS,
     "render(path, seconds=120) -> bytes\n"
     "Render a tracker module to raw PCM (44100Hz, 16-bit signed, stereo)."},
    {"get_title", mikmod_get_title, METH_VARARGS,
     "get_title(path) -> str or None\n"
     "Get the title of a tracker module."},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "mikmodplayer",
    "Python wrapper for libmikmod tracker rendering",
    -1,
    methods
};

PyMODINIT_FUNC PyInit_mikmodplayer(void) {
    return PyModule_Create(&moduledef);
}
