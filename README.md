# Dell P4317Q Control
Updated python script for controlling the Dell P4317 Monitor via RS232 Serial.

A Dell user "sredniv" posted [his](https://www.dell.com/community/user/viewprofilepage/user-id/1196431) original version of this Python script in the [Dell forums](https://www.dell.com/community/Monitors/P4317Q-RS232-interface/m-p/5078884#M109279). All the smart cleverness originated with him.  

My updates were to patch the scripts to work with the latest monitor firmware (MC104).
- Updated the checksum to include the header values
- Complete checksums required for all commands
- Updated response checksum verification to include header values
- Changed the subinput value from 0x06 to 0x07

I also included some trivial cmd script wrappers showing usage (on Windows) for some typical functions.


