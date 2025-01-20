from mutagen.flac import FLAC
import os

class song():

    def __init__(self, filepath):
        self.filepath = filepath
        self.folderpath = os.path.dirname(filepath)
        self.audio = FLAC(filepath)
        self.base_metadata = {} # Metadata to be written to the file
        self.all_metadata = {} # All available metadata
    
    def save_overwrite(self): # Saves all metadata from base_metadate into file, clearing all metadata beforehand
        self.audio.delete()
        for key in self.base_metadata.keys():
            self.audio[key] = self.base_metadata[key]
        self.audio.save()

    def save_additive(self): # Saves all metadata from base_metadata into file, without clearing metadata beforehand
        for key in self.base_metadata.keys():
            self.audio[key] = self.base_metadata[key]
        self.audio.save()