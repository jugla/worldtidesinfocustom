"""gather function objects thal allow to store data"""
# python library
import base64
import hashlib
import hmac
import os
import pickle

# Component library


def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


class File_Picture:
    """Class to manage the picture"""

    def __init__(self, path, full_path_name):
        """Initialize the data"""
        self._path = path
        self._full_path_name = full_path_name

        # check path
        ensure_dir(self._path)

    def full_filename(self):
        """give the full filename"""
        return self._full_path_name

    def store_picture_base64(self, string):
        """convert and store picture"""
        imgdata = base64.b64decode(string)
        with open(self._full_path_name, "wb") as filehandler:
            filehandler.write(imgdata)

    def remove_previous_picturefile(self):
        """remove previous file if any"""
        if os.path.isfile(self._full_path_name):
            os.remove(self._full_path_name)


class SignedPickle:
    """Class to save."""

    # This class will be save on disk
    def __init__(self, pickle_data, hmac):
        """Initialize the data."""
        self._pickle_data = pickle_data
        self._hmac = hmac


class File_Data_Cache:
    """Class to manage the data cache"""

    def __init__(self, storage_full_path, key):
        """Initialize the data."""
        self._storage_full_path = storage_full_path
        self._key = key
        self._data_read = None

    def full_filename(self):
        """give the full filename"""
        return self._storage_full_path

    def Data_Read(self):
        return self._data_read

    def Fetch_Stored_Data(self):
        """Fetch the data save on disk and check HMAC"""
        # Read previous received data
        # 1) Fetch on disk
        Fetch_Data_status = False
        Fetch_Data = None
        # 2) check HMAC
        Data_Read_Status = False
        Data_Read = None

        try:
            file_handler = open(self._storage_full_path, "rb")
            unpickler = pickle.Unpickler(file_handler)
            Fetch_Data = unpickler.load()
            file_handler.close()
            Fetch_Data_status = True
        except:
            Fetch_Data_status = False
            Fetch_Data = None

        if Fetch_Data_status:
            try:
                # Data Read is expected to be SignedPickle
                hmac_data = hmac.new(
                    self._key.encode("utf-8"), Fetch_Data._pickle_data, hashlib.sha1
                ).hexdigest()
                if hmac_data == Fetch_Data._hmac:
                    # HMACis ok. Then check if data stored correspond the current parameters
                    Data_Read = pickle.loads(Fetch_Data._pickle_data)
                    Data_Read_Status = True
                else:
                    Data_Read = None
                    Data_Read_Status = False
            except:
                Data_Read = None
                Data_Read_Status = False

        self._data_read = Data_Read
        return Data_Read_Status

    def store_data(self, data_to_store):
        """Store data on disk and compute HAMC"""

        # pickle and compute HMAC
        data_pickle = pickle.dumps(data_to_store, pickle.HIGHEST_PROTOCOL)
        hmac_data = hmac.new(
            self._key.encode("utf-8"), data_pickle, hashlib.sha1
        ).hexdigest()
        to_save = SignedPickle(data_pickle, hmac_data)

        # Dump : store received data
        file_handler = open(self._storage_full_path, "wb")
        pickler = pickle.Pickler(file_handler, pickle.HIGHEST_PROTOCOL)
        pickler.dump(to_save)
        file_handler.close()
