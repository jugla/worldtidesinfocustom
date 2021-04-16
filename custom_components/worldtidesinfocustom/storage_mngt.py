"""gather function objects thal allow to store data"""
# python library
import base64
import os

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
