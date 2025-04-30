
<img src="./images/jetsonnano1.webp" width="100%">

# Setting up your Jetson

<img src="./images/jetsonnano.jpeg" width="100%">

## Introduction
The [NVIDIA® Jetson Nano™ Developer Kit](https://developer.nvidia.com/embedded/jetson-nano-developer-kit) is a small AI computer for makers, learners, and developers. After following along with this brief guide, you’ll be ready to start building practical AI applications, cool AI robots, and more.

<div align='center'>
    <img src="./images/intro-jetson.JPG" width="80%">
</div>

---

## Write Image to the microSD Card

To prepare your microSD card, you’ll need a computer with Internet connection and the ability to read and write SD cards, either via a built-in SD card slot or adapter.

1. **Download the Jetson Nano SD Card Image:**
   - [Jetson Nano Developer Kit SD Card Image](https://developer.nvidia.com/jetson-nano-sd-card-image)
   - Note the location where it was saved.

2. **Format your microSD card using SD Card Formatter:**
   - Tool: [SD Memory Card Formatter](https://www.sdcard.org/downloads/formatter/eula_windows/)
   - Steps:
     - Select card drive
     - Select “Quick format”
     - Leave “Volume label” blank
     - Click “Format”, then “Yes” on the warning dialog

<div align='center'>
    <img src="./images/sdcard.png" width="40%">
</div>

3. **Write the image using Etcher:**
   - Tool: [Etcher](https://www.balena.io/etcher)
   - Instructions:
     - Click “Select image” and choose the zipped image file
     - Insert microSD card if not already
     - Click “Select drive” and choose correct device
     - Click “Flash!”
     - Wait ~10 minutes for flashing and validation

<div align='center'>
    <img src="./images/etcher01.png" width="60%">
</div>

<div align='center'>
    <img src="./images/etcher03.png" width="60%">
</div>

<div align='center'>
    <img src="./images/etcher02.png" width="40%">
</div>

> After flashing, Windows may show an error about reading the SD Card. Just click Cancel and remove it.

---

## Boot your Jetson

1. **Insert the microSD card** (with image flashed) into the slot on the underside of the Jetson Nano module.

<div align='center'>
    <img src="./images/insertSDcard.png" width="70%">
</div>

2. **Connect peripherals:**
   - Mouse, keyboard
   - Monitor (HDMI or DisplayPort)
   - Ethernet cable for internet access

<div align='center'>
    <img src="./images/setup_jetson.gif" width="70%">
</div>

3. **Power up:**
   - Use Micro-USB or 5V/4A DC barrel jack (J25 connector)
   - Jetson Nano will power on and boot automatically

---

## Initial Setup
   <div align='center'>
    <img src="./images/sysconf.png" width="70%">
</div>
   Follow the on-screen instructions for the initial setup, which includes:

   - Setting your language and region.
   <div align='center'>
    <img src="./images/lang.png" width="70%">
</div>

   - Connecting to a Wi-Fi network (if applicable).

   - Creating a username and password.
   <div align='center'>
    <img src="./images/login.png" width="70%">
</div>
   - Completing the NVIDIA Jetson setup wizard.

<div align='center'>
    <img src="./images/install.png" width="70%">
</div>
   This process might take a few minutes.
