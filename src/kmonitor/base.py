import json

from datetime import datetime
from collections import OrderedDict

try:
  import kubernetes
  from kubernetes import client, config
  KUBERNETES_PACKAGE_VERSION = kubernetes.__version__
  
except ImportError:
  KUBERNETES_PACKAGE_VERSION = None
#end try


from ._ver import __VER__ as __version__
from .utils.util import NPJson, safe_jsonify

from .mixins.pods_mixin import _PodsMixin
from .mixins.nodes_mixin import _NodesMixin



class KubeMonitor(
  _PodsMixin,
  _NodesMixin, 
  ):
  def __init__(self, log=None):
    super(KubeMonitor, self).__init__()
    self.log = log
    self.in_cluster = False
    self.__initialize()    
    return


  def P(self, s, **kwargs):
    if self.log is not None:
      self.log.P(s, **kwargs)
    else:
      print(s, flush=True, **kwargs)
    return
  
  @staticmethod
  def convert_memory_to_bytes(memory_str):
    """
    Converts Kubernetes memory strings to bytes.

    Parameters
    ----------
    memory_str : str
        Kubernetes memory string (e.g., "2Gi", "500Mi").

    Returns
    -------
    int
        Memory in bytes.
    """
    units = {"Ki": 1024, "Mi": 1024**2, "Gi": 1024**3, "Ti": 1024**4, "Pi": 1024**5, "Ei": 1024**6}
    unit = memory_str[-2:]
    number = float(memory_str[:-2])
    return int(number * units[unit])  


  def __initialize(self):
    if KUBERNETES_PACKAGE_VERSION is None:
      msg = "Kubernetes package not found. Please install it using 'pip install kubernetes'"
      raise ValueError(msg)
    else:
      self.P("Initializing {} v{} using kubernetes v{}".format(
        self.__class__.__name__, __version__,
        KUBERNETES_PACKAGE_VERSION,
      ))
    try:
      # Try to load in-cluster config first
      config.load_incluster_config()
      self.in_cluster = True
      self.P("  Running inside a Kubernetes cluster.")
    except config.ConfigException:
      # Fall back to kubeconfig (outside of cluster)
      config.load_kube_config()
      self.P("  Running outside a Kubernetes cluster.")
    #end try
    self.__api = client.CoreV1Api()
    self.__custom_api = client.CustomObjectsApi()
    self.P("KubeMonitor v{} initialized".format(__version__))
    return
  
  @property
  def api(self):
    return self.__api
  
  @property
  def custom_api(self):
    return self.__custom_api

  def _handle_exception(self, exc):
    error_message = f"Exception when calling Kubernetes API:\n"
    error_message += f"  Reason: {exc.reason}\n"
    error_message += f"  Status: {exc.status}\n"
    
    # Attempting to parse the body as JSON to extract detailed API response
    if exc.body:
      try:
        body = json.loads(exc.body)
        message = body.get("message")
        error_message += f"  Message: {message}\n"
      except json.JSONDecodeError:
        error_message += f"  Raw Body: {exc.body}\n"
      #end try
    #end if  
    self.P(error_message)    
    return


  def _get_elapsed(self, start_time):
    """
    Get the elapsed time since the specified start time.
    """
    return (datetime.now(start_time.tzinfo) - start_time).total_seconds()

    
  def __list_namespaces(self):
    try:
      ret = self.api.list_namespace(watch=False)
    except Exception as exc:
      self._handle_exception(exc)
      return None
    return ret.items


  ################################################################################################
  # Public methods
  ################################################################################################
  
  def get_current_namespace(self):
    """
    Get the current namespace where this code is running.
    
    Returns
    -------
    str
        The current namespace.
    """
    result = "default"
    if self.in_cluster:
      try:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace", "r") as f:
          result = f.read().strip()
      except IOError:
        self.P("Could not read namespace, defaulting to 'default'")
    return result


  def get_namespaces(self):
    """
    Get all namespaces.
    """
    lst_namespaces = self.__list_namespaces()
    return lst_namespaces


  def list_namespaces(self):
    """Get all namespaces."""
    return self.get_namespaces()
