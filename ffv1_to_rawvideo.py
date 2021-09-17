# =============================================================================
# MIT License
# 
# Copyright (c) 2021 luckytyphlosion
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# =============================================================================

from guietta import Gui, QFileDialog, _, Exceptions, QLineEdit, QMessageBox, QPushButton, QIcon
import pathlib
import configparser
import subprocess
import time
import platform
import ctypes
import os

# filename = QFileDialog.getOpenFileName(None, "Open File",
#                                              "/home",
#                                              "Images (*.png *.xpm *.jpg *.jpeg)")
# 
# print(filename)

def read_config():
    config_filepath = pathlib.Path("config.ini")
    if config_filepath.is_file():
        with open(config_filepath, "r") as f:
            config = configparser.ConfigParser(allow_no_value=True)
            config.read_file(f)
    else:
        config = configparser.ConfigParser(allow_no_value=True)
        config["Directories"] = {
            "InputAVIDirectory": "",
            "OutputAVIDirectory": ""
        }

        serialize_config(config)

    return config

def serialize_config(config):
    with open("config.ini", "w+") as f:
        config.write(f)

def write_and_serialize_config(config, section, key, value):
    config[section][key] = value
    serialize_config(config)

def get_avi(config, config_key, editline, q_file_dialog_func, caption):
    filename_tuple = q_file_dialog_func(None, caption,
                                            config["Directories"][config_key],
                                            "AVI files (*.avi)"
    )
    #print(f"filename_tuple: {filename_tuple}")
    avi_filename = filename_tuple[0]
    if avi_filename != "":
        avi_filepath = pathlib.Path(avi_filename)
        avi_folder_name = str(avi_filepath.parent.resolve())
        write_and_serialize_config(config, "Directories", config_key, avi_folder_name)

        #print(avi_filename)
    editline.setText(avi_filename)

def wait_ffmpeg_finish(ffmpeg_process):
    while True:
        return_code = ffmpeg_process.poll()
        if return_code is not None:
            break
        else:
            time.sleep(0.25)

    if return_code == 0:
        return True
    else:
        error_output = ""
        error_output += f"return code: {return_code}\n"
        error_output += "=== stderr below ===\n"
        try:
            stdout, stderr = ffmpeg_process.communicate(timeout=5)
            error_output += f"{stderr}\n"
        except TimeoutExpired:
            ffmpeg_process.kill()
            error_output += "Something went wrong while trying to retrieve error information\n"

        with open("error.log", "w+") as f:
            f.write(error_output)

        return False

class Gui2(Gui):
    def _close_handler(self, event):
        if self.converting_avi and self.ffmpeg_process.poll() is None:
            self.ffmpeg_process.terminate()
            while self.ffmpeg_process.poll() is None:
                time.sleep(0.1)

            pathlib.Path(self.output_filename).unlink(missing_ok=True)
        super()._close_handler(event)

    def set_icon(self, filename):
        app_icon = QIcon()
        app_icon.addFile(filename)
        self._app.setWindowIcon(app_icon)
        if platform.system() == "Windows":
            app_id = 'taslabz.ffv1_to_rawvideo.qm.1' # arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

def main():
    
    config = read_config()
    input_avi_filename_editline = QLineEdit("")
    output_avi_filename_editline = QLineEdit("")
    convert_button = QPushButton("Convert")

    converting_avi = False

    gui = Gui2(
        ["Input AVI", input_avi_filename_editline, ["Open"]],
        ["Output AVI", output_avi_filename_editline, ["Save"]],
        [_, convert_button, _],
        exceptions = Exceptions.OFF
    )

    gui.converting_avi = False
    gui.ffmpeg_process = None
    gui.set_icon("gui/i_love_ffmpeg.png")

    def get_input_avi(gui, *args):
        get_avi(config, "InputAVIDirectory", input_avi_filename_editline, QFileDialog.getOpenFileName, "Open File")

    def get_output_avi(gui, *args):
        get_avi(config, "OutputAVIDirectory", output_avi_filename_editline, QFileDialog.getSaveFileName, "Save File")

    def convert_avi(gui, *args):
        if gui.converting_avi:
            return

        input_filename = input_avi_filename_editline.text()
        input_filepath = pathlib.Path(input_filename)
        output_filename = output_avi_filename_editline.text()

        error_msg = ""

        if input_filename == "":
            error_msg += "- Input AVI is not specified!\n"
        elif not input_filepath.is_file():
            error_msg += "- Input AVI does not exist or is not a file!\n"
        if output_filename == "":
            error_msg += "- Output AVI is not specified!\n"

        if error_msg != "":
            QMessageBox.critical(None, "Error", f"Error occurred!\n{error_msg}")
            return

        #with open("log.txt", "w+") as f:
        #    f.write(f"os.getcwd(): {os.getcwd()}")

        convert_button.setEnabled(False)
        convert_button.setText("Converting...")
        gui.converting_avi = True
        gui.ffmpeg_process = subprocess.Popen(
            ("ffmpeg/ffmpeg.exe", "-y", "-i", input_filename, "-c:v", "rawvideo", "-pix_fmt", "bgr24", output_filename),
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="ascii"
        )
        gui.output_filename = output_filename
        gui.execute_in_background(wait_ffmpeg_finish, args=(gui.ffmpeg_process,), callback=after_ffmpeg_finish)

    def after_ffmpeg_finish(gui, ret_value):
        if ret_value:
            QMessageBox.information(None, "Information", "Converted!")
        else:
            QMessageBox.critical(None, "Error", "Something went wrong. Details can be found in error.log")

        convert_button.setEnabled(True)
        convert_button.setText("Convert")
        gui.converting_avi = False

    gui.events(
        [_, _, get_input_avi],
        [_, _, get_output_avi],
        [_, convert_avi, _]
    )

    #print("Running!")

    try:
        gui.run()
    except Exception as e:
        exception_output = f"Exception occurred: {e}\n{''.join(traceback.format_tb(e.__traceback__))}\n"
        with open("exception.log", "w+") as f:
            f.write(exception_output)

        raise RuntimeError(e)

if __name__ == "__main__":
    main()
