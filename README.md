

## Install
* Update
    ```
    opkg update
    ````
* Driver for USB serial
    ```
    opkg install kmod-usb-acm
    ```
* MQTT brouker
    ```
    opkg install mosquitto mosquitto-client
    ```
* Python3 and dependency
    ```
    opkg install python3 python3-pyserial python3-pip
    pip3 install paho-mqtt docopt
    ```

```
/etc/init.d/mosquitto enable
/etc/init.d/mosquitto start
```
