"""
Parameters for the Impatient Cosmologist
Author: Marius Millea
"""

__version__ = '3.3.0'

import pickle, imp, os, sys, numpy, hashlib, time
from distutils.sysconfig import get_config_var, PREFIX, get_python_inc

""" Loaded datafiles will reside in this empty module. """
sys.modules['pypico.datafiles']=imp.new_module('pypico.datafiles')

def get_folder():
    """Get the folder where PICO was installed"""
    return os.path.dirname(os.path.abspath(__file__))

def get_include():
    """Get include flags needed for compiling C/Fortran code with the PICO library."""
    return ' '.join(['-I' + get_python_inc(),
                     '-I' + get_python_inc(plat_specific=True),
                     '-I%s'%numpy.get_include(),
                     '-I%s'%os.path.dirname(os.path.abspath(__file__))])

def get_link():
    """Get link flags needed for linking C/Fortran code with the PICO library."""
    return ' '.join(['-L%s -lpico '%os.path.dirname(os.path.abspath(__file__)),
                     '-L%s/lib'%PREFIX.strip()] +
                    get_config_var('LIBS').split() +
                    get_config_var('SYSLIBS').split() +
                    ['-lpython' + get_config_var('VERSION')])


class PICO():
    """
    This is the base class for anyone creating a custom PICO datafile.
    It represents a mapping from input values to output values.

    Note that if the input values are scalars and the output values
    are vectors, then the code in this library can be used to call the
    PICO object from C/Fortran.

    The fundamental methods are inputs() and outputs() which list possible
    inputs and returned outputs, and get(**inputs) which gets the outputs
    given some inputs.
    """

    def inputs(self):
        """
        Returns a list of strings corresponding to names of valid inputs.
        The get() method accepts keyword arguments corresponding to these inputs.
        """
        raise NotImplementedError


    def outputs(self):
        """
        Returns a list of strings corresponding to names of possible outputs.
        The get() method returns a dictionary with keys corresponding to these outputs.
        """
        raise NotImplementedError

    def get(self,outputs=None,**inputs):
        """
        Evaluate this PICO function for the given **inputs.
        The keyword argument 'outputs' can specify a a subset of outputs
        to actually calculate, or it can be None to calculate all outputs
        returned by PICO.outputs()
        """
        raise NotImplementedError


class CantUsePICO(Exception):
    """
    This Exception is raised if for any reason
    (including bad input values, failure load some files, etc...)
    PICO.get() cannot compute the result.
    """
    pass



def _version_ok(version):
    """Checks for compatibility of a PICO datafile."""
    mine = list(map(int,__version__.split('.')))
    theirs = list(map(int,__version__.split('.')))
    return mine[0]==theirs[0] and mine[1]>=theirs[1]


def load_pico(datafile, verbose=False, module=None, check_version=True):
    """
    Load a PICO data datafile and return a PICO object.

    Parameters
    ----------

    datafile :
        Path to the PICO datafile
    verbose, optional :
        Whether to print debugging messages during calculation. (default: False)
    check_version, optional :
        Can set to False to force PICO to use an old datafile. (default: False)
    module, optional :
        If not None, it can specify a path to a Python file, which will
        used instead of the code contained in the datafile. This is generally
        used for debugging purposes only. (default: None)
    """

    try:
        with open(datafile, "rb") as f: data = pickle.load(f)
    except Exception as e:
        raise Exception("Failed to open PICO datafile '%s'\n%s"%(datafile,e.message))

    if module:
        imp.load_source(data['module_name'],module)
    else:
        if data['module_name'] not in sys.modules:
            code = data['code']
            try:
                mymod = imp.new_module(data['module_name'])
                exec(code, mymod.__dict__)
                sys.modules[data['module_name']]=mymod
            except Exception as e:
                raise Exception("Error executing PICO code for datafile '%s'\n%s"%(datafile,e))

    if check_version:
        if 'version' not in data:
            print("Warning: PICO datafile does not have version. Can't check compatibility.")
        elif not _version_ok(data.get('version')):
            raise Exception("Your PICO version (%s) and the PICO version used to create the datafile '%s' (%s) are incompatible. Rerun with check_version=False to ignore this message."%(_version,datafile,data['version']))


    pico = pickle.loads(data['pico'], encoding="latin1")
    data.pop('pico')
    pico._pico_data = data
    return pico


def create_pico(codefile,datafile,args=None,existing_pico=None):
    """
    Create a PICO datafile.

    A PICO datafile is a Pickle of a dictionary which contains
    some Python code and an instance of a PICO class.

    Parameters
    ----------
        codefile :
            A path to a Python module which contains a ``get_pico(*args)`` function.
            The function should return a ``PICO`` object which gets Pickled into the
            datafile.
        datafile :
            Path for the output datafile
        args, optional :
            Passed to get_pico(*args)
        existing_pico, optional :
            Don't call ``get_pico``, just bundle up this existing
            PICO object with the given code
    """

    print("Creating PICO datafile...")
    if existing_pico is None:
        name = 'pypico.datafiles.%s'%(hashlib.md5(os.path.abspath(codefile) + time.ctime()).hexdigest())
        mymod = imp.load_source(name,codefile)
        pico = mymod.get_pico(*args)
    else:
        pico = load_pico(existing_pico)
        name = pico._pico_data['module_name']
    print("Saving '%s'..."%(os.path.basename(datafile)))
    with open(datafile,'w') as f: pickle.dump({'code':open(codefile).read(),
                                                'module_name':name,
                                                'pico':pickle.dumps(pico,protocol=2),
                                                'version':__version__},
                                                f,protocol=2)
