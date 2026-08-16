# Install Integration

If you haven't added the repository to `HACS`.

[:simple-homeassistantcommunitystore: Add repository to HACS](https://my.home-assistant.io/redirect/hacs_repository/?category=integration&repository=hass-localtuya&owner=airy10){ target=_blank .md-button }

<!-- ??? note "Add Repository Manually"
    1. Go to `HACS` and navigate to Integrations Section
    2. Click on :material-dots-vertical: in the top right corner and click on Custom repositories
    3. Paste `https://github.com/airy10/hass-localtuya` into the input field and select Integration from the category dropdown then click ADD
    4. Now the integration should be added search in for it and install it!. -->

<Br>

#### Add HUB
1. Adding hub options:

    a. Go to the [integration page](https://my.home-assistant.io/redirect/integrations/){target=_blank} in HA and click on `ADD INTEGRATION` in the bottom right corner.

    b. Or use [MY: Add Integration](https://my.home-assistant.io/redirect/config_flow_start/?domain=localtuya){target=_blank}
<br><br>

2. Adding a new hub will introduce you to this configuration page (1)<br>
{ .annotate }

    1. ![](../images/init.png)
    
    a. If you prefer not to set up the cloud API, choose `Log in with Tuya IoT Platform credentials (Legacy)` and check `Disable Cloud API?`

    b. If you've set up a `cloud` account, you should have all the necessary information
    <br> [Get authentication data](../cloud_api.md/#get-authorization-data).

!!! note "BLE devices"
    To add BLE devices you **must** configure a cloud API account, as BLE credentials and specs are fetched from the cloud. BLE devices are then added through `Options` -> `Add a BLE device` (see [Add new devices](configure_add_device.md#add-a-ble-device)).

