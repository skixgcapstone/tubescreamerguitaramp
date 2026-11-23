# Demo quick start

## Connect before powering on

1. Connect the Pi 5's micro-HDMI port to the ELECROW display's HDMI input. Use the HDMI cable/adapter that fits the actual display and Pi.
2. Connect the display's USB touch port to a Pi USB port. Connect any separate display power required by the specific unit and its manual. The HDMI cable is for video; do not assume it supplies display power.
3. Connect the guitar and the tested tube-board/codec signal path. For the powered speaker, use the codec's **P2 AUX OUT**, not the green speaker terminals. If using the PCB's master volume, route P2 to J4 and the PCB J6 output to the powered speaker. Set speaker volume low before turning on, then raise it.
4. Power the display and then the Pi. Wait about a minute. The desktop should sign in and launch the Tube Screamer app automatically; no Codex or Ethernet connection is needed for normal operation. Temporary music playback does not restart after a reboot.

The ELECROW screen has not yet been connected to this Pi. Exact port labels, cable needs, automatic HDMI resolution and touch alignment must be checked on the actual unit. If the screen is black, confirm the display is powered and on the correct HDMI input and reseat the HDMI and touch cables. Restart the Pi with the display already powered and connected. Do not change the existing boot configuration based on generic monitor instructions without recording the original settings.

## Run the demo

1. Confirm the app shows `AUDIO: PLAYING`. If it is still starting, give it another minute.
2. Play the guitar. Open **EQ + WAVEFORMS** to check input and output and open **System Status** to check levels and errors.
3. Open **Effects** and tap an effect to turn it on. Drag on its pad to adjust. Adjust the PCB master and powered-speaker volume as needed.
4. When finished, shut down using the desktop's power menu; wait for the Pi to shut down before disconnecting power.

## If there is no sound

- Check speaker power, its volume, the PCB master control, and the guitar volume.
- Check codec P1 AUX IN and P2 AUX OUT wiring, including audio grounds. Keep all wiring changes powered off.
- Check that the app says `AUDIO: PLAYING`. After startup it uses the codec AUX output at 0 dB; it does not enable the separate green passive-speaker terminals.
- If the input waveform and System Status do not respond while playing, inspect the guitar cable and input connection first. If the input responds but output is quiet, inspect output/volume/speaker connections. Do not connect a speaker or codec input to a tube plate or bypass the PCB's DC blocking capacitor.
- The controls can temporarily change gain and level; turn down the speaker while reconnecting and increase gradually.

## If the app is missing

Use a USB mouse/keyboard, or SSH if available, and run:

```sh
systemctl --user status tube-screamer.service --no-pager -l
systemctl --user restart tube-screamer.service
```

If the touchscreen appears but touches are offset, use a mouse and the Raspberry Pi screen-configuration tool; ask the team member with Pi access to configure the new display and touch mapping. No network or keyboard can correct a disconnected display or speaker cable.

If the temporary Cliffs of Dover test is still playing and you need to switch
back to live input without rebooting, open a terminal on the Pi and run:

```sh
~/capstoneSoftwareDemo/deploy/start-demo.sh
```
