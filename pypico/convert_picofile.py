def convert_picofile(datafile, codefile):
    """
    Convert a serialized pico file from python 2 to python 3

    Parameters
    ----------

    datafile :
        Path to the PICO datafile
    codefile :
        A path to a Python module which contains a ``get_pico(*args)`` function.
        The function should return a ``PICO`` object which gets Pickled into the
        datafile.

    """
    import pickle
    with open(datafile, "rb") as f: old = pickle.load(f, encoding="bytes")
    new = {}
    new["code"] = open(codefile).read()
    new["module_name"] = old[b"module_name"].decode("ascii")
    new["version"] = old[b"version"].decode("ascii")
    new["pico"] = old[b"pico"]

    import os
    newdatafile = os.path.splitext(datafile)[0] + "_py3.dat"
    pickle.dump(new, open(newdatafile, "wb"), protocol=4)
