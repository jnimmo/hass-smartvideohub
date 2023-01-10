# hass-smartvideohub
Home Assistant integration for the Blackmagic Smart Videohub

Blackmagic provide an API to allow control of their video switches over TCP. This asynchronous interface will update Home Assistant if any changes are made on the device directly or elsewhere.

It works well with the [Universal Media Player](https://home-assistant.io/components/media_player.universal/) as you could power TVs/projectors on or off then point the source and source select options at the outputs created by this platform to be able to select the source. 

### Usage

To use Smart Video Hub in your installation:
1. Download the pyvideohub.py file and save to custom_components folder in your configuration directory
2. Create a subdirectory inside custom_components called media_player
3. Download the smartvideohub.py file and save to the custom_components/media_player directory
4. Add the following to the configuration file

```yaml
media_player
  - platform: smartvideohub
    host: 192.168.2.10
    port: 9990
    name: Videohub
```

Configuration variables:
- **host** (*Required*): IP address of the Blackmagic Smart Videohub
- **port** (*Required*): Default to 9990
- **name** (*Required*): This will be used to prefix the output names in Home Assistant
- **hide_default_inputs** (Optional): Set to True to hide inputs which have not been renamed from the default

Supported features:
- Source select
- Source list
