<a  href="https://www.buymeacoffee.com/mrbanderx3"  target="_blank"><img  src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png"  alt="Buy Me A Coffee"  style="height: 30px !important;width: 150px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>

---


![logo](https://github.com/rospogrigio/localtuya-homeassistant/blob/master/img/logo-small.png)


__A Home Assistant custom Integration for local handling of Tuya-based Ethernet (Wifi) or BLE devices.__

### **Usage and setup [Documentation](https://airy10.github.io/hass-localtuya/)**

<br>

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?category=integration&repository=hass-localtuya&owner=airy10)


This https://xzetsubou.github.io/hass-localtuya/ clone is an experiment mix of xzetsubou localtuya component to control Ethernet devices, my ha_tuya_ble component for BLE devices (https://github.com/airy10/ha_tuya_ble) and Home Assistant Core Tuya component (in order to have entities created/handled the same way as with the cloud core component).
The goal is to be able to control Tuya devices (Ethernet ones and BLE ones) locally - the Tuya Cloud is optionally used to automatically discover and configure local devices. After a device is configured, the cloud shouldn't be needed at all to control the device from Home Assistant.
This is still very experimental and tested only with the devices I own.
Full documentation hasn't been updated yet.

AI agents were heavily used to merge these three Tuya components.


## __𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬__
- Supports both Wifi and BLE devices
- Auto-configure devices - `Requires a cloud API setup`
- Automatic insertion - `Some fields requires a cloud API setup`
- Devices discovery - `Discovers Tuya devices on your network`
- Cloud API - `Only to help you to setup devices, can work without it.`


<br>

[𝐑𝐞𝐩𝐨𝐫𝐭𝐢𝐧𝐠 𝐚𝐧 𝐢𝐬𝐬𝐮𝐞](https://airy10.github.io/hass-localtuya/report_issue/)

<!-- ### Notes

* Do not declare anything as "tuya", such as by initiating a "switch.tuya". Using "tuya" launches Home Assistant's built-in, cloud-based Tuya integration in lieu of localtuya.

* This custom integration updates device status via pushing updates instead of polling, so status updates are fast (even when manually operated).

* The integration also supports the Tuya IoT Cloud APIs, for the retrieval of info and of the local_keys of the devices. 
The Cloud API account configuration is not mandatory (LocalTuya can work also without it) but is strongly suggested for easy retrieval (and auto-update after re-pairing a device) of local_keys. Cloud API calls are performed only at startup, and when a local_key update is needed. -->

<details><summary> 𝐂𝐫𝐞𝐝𝐢𝐭𝐬 </summary>
<p>
    
[PlusPlus-ua](https://github.com/PlusPlus-ua), the original creator of my ha_tuya_ble integration
[xZetsubou](https://github.com/xZetsubou), the author of the LocalTuya component I used as a basis for this project

</p>
</details> 
