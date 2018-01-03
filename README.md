# hass-smartvideohub
Home Assistant integration for the Blackmagic Smart Videohub

Blackmagic provide an API to allow control of their video switches over TCP. This asynchronous interface will update Home Assistant if any changes are made on the device directly or elsewhere.

It works well with the [Universal Media Player](https://home-assistant.io/components/media_player.universal/) as you could power TVs/projectors on or off then point the source and source select options at the outputs created by this platform to be able to select the source. 

### Usage

To use DMX in your installation:
1. Download the pyvideohub.py file and save to custom_components folder in your configuration directory
2. Create a subdirectory inside custom_components called media_player
3. Download the smartvideohub.py file and save to the custom_components/media_player directory
4. Add the following to the configuration file

```yaml
media_player:
  - platform: smartvideohub
    host: <IP address>
    port: 9990
    name: videohub
```

Configuration variables:
- **host** (*Required*): IP address of the Blackmagic Smart Videohub
- **port** (*Required*): Default to 9990
- **name** (*Required*): This will be used to prefix the output names in Home Assistant

Supported features:
- Source select
- Source list

Limitations:
- Currently the platform isn't dealing with disconnections or if it can't connect to the Videohub- this is on the to do list.
- There is no way to hide inputs from the source select option which aren't in use; it is on the to do list to be able to specify which inputs should be available on each device if desired.
