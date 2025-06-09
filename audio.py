import pyaudio
import socket
import struct
import threading
from PyQt5.QtCore import QObject, pyqtSignal

# Настройки аудио
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
BUFFER_SIZE = 1024

class AudioHandler(QObject):
    disconnect_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.sock_audio = None
        self.connected = False
        self.audio = pyaudio.PyAudio()
        self.stream_in = None
        self.stream_out = None
        self.receive_thread = None
        self.record_thread = None

    def start_audio(self, host, port, login, channel_id):
        try:
            self.sock_audio = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock_audio.connect((host, port))
            login_bytes = login.encode('utf-8').ljust(1024, b'\x00')
            data = struct.pack('!1024sQ', login_bytes, channel_id)
            self.sock_audio.sendall(data)

            self.audio = pyaudio.PyAudio()  # Инициализируем новый экземпляр PyAudio
            self.stream_in = self.audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK, input_device_index=None)
            self.stream_out = self.audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK, output_device_index=None)
            self.connected = True

            self.receive_thread = threading.Thread(target=self.receive_audio, daemon=True)
            self.receive_thread.start()
            self.record_thread = threading.Thread(target=self.record_audio_thread, daemon=True)
            self.record_thread.start()
            return True
        except Exception as e:
            self.disconnect()
            print(f"Audio start error: {str(e)}")
            return str(e)

    def receive_audio(self):
        while self.connected:
            try:
                data = self.sock_audio.recv(BUFFER_SIZE)
                if not data:
                    self.disconnect_signal.emit()
                    break
                self.stream_out.write(data, exception_on_underflow=False)
            except Exception:
                self.disconnect_signal.emit()
                break

    def record_audio_thread(self):
        while self.connected:
            try:
                data = self.stream_in.read(CHUNK, exception_on_overflow=False)
                self.sock_audio.sendall(data)
            except Exception:
                self.disconnect_signal.emit()
                break

    def disconnect(self):
        if not self.connected:
            return
        self.connected = False
        try:
            if self.stream_in:
                self.stream_in.stop_stream()
                self.stream_in.close()
                self.stream_in = None
            if self.stream_out:
                self.stream_out.stop_stream()
                self.stream_out.close()
                self.stream_out = None
            if self.sock_audio:
                self.sock_audio.close()
                self.sock_audio = None
            if self.audio:
                self.audio.terminate()
                self.audio = None
        except Exception as e:
            print(f"Audio disconnect error: {str(e)}")
        finally:
            self.disconnect_signal.emit()

    def close(self):
        self.disconnect()
        if self.audio:
            self.audio.terminate()
            self.audio = None