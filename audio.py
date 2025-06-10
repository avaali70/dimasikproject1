import pyaudio
import socket
import struct
import threading
import platform
import logging
from PyQt5.QtCore import QObject, pyqtSignal
import chardet

# Настройка логирования
logging.basicConfig(
    filename="audio_devices.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

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
        self.input_device_index = None
        self.output_device_index = None

    def get_audio_devices(self):
        """Возвращает списки микрофонов и динамиков, только подключенные, с корректной кодировкой."""
        input_devices = []
        output_devices = []
        seen_names = set()
        is_windows = platform.system() == "Windows"
        
        for i in range(self.audio.get_device_count()):
            try:
                device_info = self.audio.get_device_info_by_index(i)
                raw_name = device_info['name']
                
                # Обработка кодировки
                if is_windows:
                    try:
                        # Проверяем, является ли raw_name уже строкой (иногда PyAudio возвращает декодированную строку)
                        if isinstance(raw_name, str):
                            name = raw_name
                        else:
                            # Декодируем как UTF-8
                            name = raw_name.decode('utf-8', errors='replace')
                    except Exception:
                        name = raw_name  # Fallback на исходное имя
                else:
                    # Для Linux используем chardet
                    detection = chardet.detect(raw_name.encode('utf-8', errors='ignore'))
                    encoding = detection['encoding'] or 'utf-8'
                    try:
                        name = raw_name.encode('utf-8').decode(encoding, errors='replace')
                    except Exception:
                        name = raw_name
                
                # Логируем и выводим в консоль для диагностики
                logging.debug(f"Device index: {i}, Raw name: {repr(raw_name)}, Decoded name: {name}")
                print(f"Device index: {i}, Raw name: {repr(raw_name)}, Decoded name: {name}")
                
                if device_info.get('maxInputChannels', 0) == 0 and device_info.get('maxOutputChannels', 0) == 0:
                    continue
                try:
                    test_stream = self.audio.open(
                        format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=(device_info.get('maxInputChannels', 0) > 0),
                        output=(device_info.get('maxOutputChannels', 0) > 0),
                        frames_per_buffer=CHUNK,
                        input_device_index=i if device_info.get('maxInputChannels', 0) > 0 else None,
                        output_device_index=i if device_info.get('maxOutputChannels', 0) > 0 else None
                    )
                    test_stream.close()
                except Exception:
                    logging.debug(f"Device index: {i} is not accessible, skipping")
                    continue
                
                # Улучшенная фильтрация дубликатов: используем имя, hostApi и каналы
                unique_key = (name, device_info.get('hostApi', -1), device_info.get('maxInputChannels', 0), device_info.get('maxOutputChannels', 0))
                if unique_key in seen_names:
                    continue
                seen_names.add(unique_key)
                
                device = {
                    'index': device_info['index'],
                    'name': name,
                    'maxInputChannels': device_info.get('maxInputChannels', 0),
                    'maxOutputChannels': device_info.get('maxOutputChannels', 0)
                }
                
                if device_info.get('maxInputChannels', 0) > 0:
                    input_devices.append(device)
                if device_info.get('maxOutputChannels', 0) > 0:
                    output_devices.append(device)
            
            except Exception as e:
                logging.debug(f"Error processing device index {i}: {str(e)}")
                continue
        
        return input_devices, output_devices

    def change_input_device(self, input_device_index):
        """Переключает устройство ввода на горячую."""
        try:
            if self.stream_in and self.connected:
                self.stream_in.stop_stream()
                self.stream_in.close()
                self.stream_in = None
            self.input_device_index = input_device_index
            if self.connected:
                self.stream_in = self.audio.open(
                    format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK,
                    input_device_index=self.input_device_index
                )
        except Exception as e:
            print(f"Error changing input device: {str(e)}")
            self.disconnect_signal.emit()

    def change_output_device(self, output_device_index):
        """Переключает устройство вывода на горячую."""
        try:
            if self.stream_out and self.connected:
                self.stream_out.stop_stream()
                self.stream_out.close()
                self.stream_out = None
            self.output_device_index = output_device_index
            if self.connected:
                self.stream_out = self.audio.open(
                    format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    output=True,
                    frames_per_buffer=CHUNK,
                    output_device_index=self.output_device_index
                )
        except Exception as e:
            print(f"Error changing output device: {str(e)}")
            self.disconnect_signal.emit()

    def start_audio(self, host, port, login, channel_id, input_device_index=None, output_device_index=None):
        try:
            self.sock_audio = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock_audio.connect((host, port))
            login_bytes = login.encode('utf-8').ljust(1024, b'\x00')
            data = struct.pack('!1024sQ', login_bytes, channel_id)
            self.sock_audio.sendall(data)

            self.audio = pyaudio.PyAudio()
            self.input_device_index = input_device_index
            self.output_device_index = output_device_index
            self.stream_in = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
                input_device_index=self.input_device_index
            )
            self.stream_out = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                output=True,
                frames_per_buffer=CHUNK,
                output_device_index=self.output_device_index
            )
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

    def record_audio(self):
        data = self.stream_in.read()
        if self.parent().MICROPHONE_ENABLED == 1:
            return data

    def change(self,):
        while self.connected:
            try:
                data = self.record_audio(CHUNK, exception_on_overflow=False)
                self.sock_audio.send_data(data)
            except Exception:
                self.disconnect_signal.emit()
                break

    def disconnect(self):
        if not self.connected:
            return
        self.is_connected = False
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