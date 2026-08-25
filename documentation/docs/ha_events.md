# Events
!!! note ""
    Your device must be added to localtuya to use Events

Localtuya fires an [events](https://www.home-assistant.io/docs/configuration/events/){target="_blank"} on `homeassisstant` 
that can be used on automation or monitoring your device behaviour from [Developer tools -> events](https://my.home-assistant.io/redirect/developer_events/){target="_blank"} (1)<Br>
{.annotate}

1. to monitor your device subscribe to any event below and trigger action on the device using tuya app


!!! annotate tip ""
    With this you can automate devices such as `scene remote` (1) to trigger an action on `homeassistant`

1. e.g. `single click`, `double click` or `hold`.

| Event                             | Data                                  
| --------------------------------- | ------------------------------------ 
| `localtuya_status_update`         | `#!json {"data": {"device_id", "old_status", "new_status"} }` 
| `localtuya_device_dp_triggered`   | `#!json {"data": {"device_id", "dp", "value"} }`              
| `localtuya_fingerbot_button_pressed` | `#!json {"data": {"device_id"} }`            


Examples 
=== "localtuya_states_update"

    ```yaml title=""
    # This will only triggers if status changed.
    trigger:
      - platform: event
        event_type: localtuya_status_update
    condition: []
    action:
      - service: persistent_notification.create
        data:
          message: "{{ trigger.event.data }}"

    ```

=== "localtuya_device_dp_triggered"

    ```yaml title=""
    # This will always triggers if DP used.
    trigger:
      - platform: event
        event_type: localtuya_device_dp_triggered
    condition: []
    action:
      - service: persistent_notification.create
        data:
          message: "{{ trigger.event.data }}"

    ```
    ??? example "example of an automation to trigger a scene when the first button on a remote is single-clicked"
        ```yaml title=""
        
        trigger:
          - platform: event
            event_type: localtuya_device_dp_triggered
            event_data:
              device_id: bfa2f86e3068440a449dhd
              dp: "1" # quotes are important for dp
              value: single_click 
        condition: []
        action:
          - service: persistent_notification.create
            data:
              message: "{{ trigger.event.data }}"

        ```

=== "localtuya_fingerbot_button_pressed"

    ```yaml title=""
    # Fired on the HA bus when a BLE fingerbot's physical button is pressed.
    trigger:
      - platform: event
        event_type: localtuya_fingerbot_button_pressed
    condition: []
    action:
      - service: persistent_notification.create
        data:
          message: "{{ trigger.event.data }}"

    ```

!!! note "Event platform entities"
    Some devices (e.g. doorbells, scene remotes, fingerbots) are exposed as `event` entities (the `Event` platform). For those, subscribe to the entity's `pressed` event type instead of using raw `localtuya_device_dp_triggered`. BLE fingerbots also fire `localtuya_fingerbot_button_pressed` on the HA bus.

!!! note "BLE lock & Fingerbot entities"
    BLE devices additionally get automatically created event entities that fire on every device report - not only on value changes:

    - **Unlocked by** (`event_type`: `fingerprint`, `password`, `card`, ... with a `credential_id` attribute) - created for BLE locks that report how they were opened, even if they expose no controllable lock.
    - **Fingerbot button** (`event_type`: `pressed`) - created for known Fingerbot products when their physical button is pressed.

    The first report of each datapoint right after a (re)connect is ignored: locks and similar devices replay their last stored values on connection, which is history rather than an event.

!!! annotate warning "Database flooding"
    If the recorder is enabled, devices like temperature sensors may update frequently (e.g., every second). 
    This can cause excessive events and significantly increase database size. 
    It is recommended to exclude _localtuya_ events from the recorder to prevent database overload.
    !!! annotate tip ""
        ```yaml title=""
        recorder:
          exclude:
            event_types:
              - localtuya_status_update
              - localtuya_device_dp_triggered
              - localtuya_fingerbot_button_pressed
        ```