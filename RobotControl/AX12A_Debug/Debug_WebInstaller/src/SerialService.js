export class SerialService {
  constructor() {
    this.port = null;
    this.reader = null;
    this.writer = null;
    this.onMessage = null;
    this.onDisconnect = null;
    this.keepReading = true;
  }

  async connect() {
    try {
      this.port = await navigator.serial.requestPort();
      await this.port.open({ baudRate: 115200 }); // ESP32 Serial.begin rate
      
      this.keepReading = true;
      this.startReading();
      
      return true;
    } catch (error) {
      console.error("Failed to connect to serial port", error);
      return false;
    }
  }

  async disconnect() {
    this.keepReading = false;
    if (this.reader) {
      await this.reader.cancel();
    }
    if (this.writer) {
      this.writer.releaseLock();
    }
    if (this.port) {
      await this.port.close();
    }
    this.port = null;
    if (this.onDisconnect) this.onDisconnect();
  }

  async startReading() {
    const textDecoder = new TextDecoderStream();
    this.port.readable.pipeTo(textDecoder.writable);
    this.reader = textDecoder.readable.getReader();

    let buffer = "";
    
    try {
      while (this.keepReading) {
        const { value, done } = await this.reader.read();
        if (done) break;
        
        if (value) {
          buffer += value;
          const lines = buffer.split("\n");
          // Keep the last partial line in the buffer
          buffer = lines.pop();
          
          for (let line of lines) {
            line = line.trim();
            if (line.startsWith("{") && line.endsWith("}")) {
              try {
                const data = JSON.parse(line);
                if (this.onMessage) this.onMessage(data);
              } catch (e) {
                console.warn("Failed to parse JSON line:", line);
              }
            } else if (line.length > 0) {
              console.log("ESP32:", line);
            }
          }
        }
      }
    } catch (error) {
      console.error("Error reading from serial port", error);
    } finally {
      if (this.reader) {
        this.reader.releaseLock();
      }
      this.disconnect();
    }
  }

  async sendCommand(command) {
    if (!this.port) return;
    
    if (!this.writer) {
      const textEncoder = new TextEncoderStream();
      textEncoder.readable.pipeTo(this.port.writable);
      this.writer = textEncoder.writable.getWriter();
    }
    
    await this.writer.write(command + "\n");
  }
}

export const serialService = new SerialService();
