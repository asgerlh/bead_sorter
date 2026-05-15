import os

class ColorDataFile:
    """Manages color data file creation and writing."""
    def __init__(self):
        self.file = None
        self.file_number = 0
        self._load_file_number()

    def _load_file_number(self):
        """Pre-scan existing files to set file_number."""
        files = os.listdir("data")
        for f in files:
            if f.startswith("colors") and f.endswith(".csv"):
                num = int(f[len("colors"):-4])
                if num > self.file_number:
                    self.file_number = num

    def open(self):
        """Open a new color data file and write header.

        Closes any existing file first to ensure clean state.
        """
        self.close()  # Close existing file if any
        self.file_number += 1
        try:
            self.file = open("data/colors{}.csv".format(self.file_number), "w")
            self.file.write("R, G, B, C\n")
        except Exception:
            self.file = None
            raise

    def write(self, rgbc):
        """Write RGBC data to file if open."""
        if self.file is not None:
            try:
                self.file.write("{}, {}, {}, {}\n".format(*rgbc))
            except Exception:
                self.close()
                raise

    def close(self):
        """Safely close the color data file."""
        try:
            if self.file is not None:
                self.file.close()
        except Exception:
            pass
        finally:
            self.file = None
