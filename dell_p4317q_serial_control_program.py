#!/usr/bin/python

import sys
import struct
import serial
import binascii

debug=False

CMD_HEADER=bytearray([0x37, 0x51])
CMD_READ=0xEB
CMD_WRITE=0xEA

# Only get commands have a response.
RSP_HEADER=bytearray([0x6F, 0x37])
RSP_REPLY_CODE=0x02

def print_debug(message):
    "Debug print message"
    if (debug == True):
        print message

def print_usage():
    "Print program usage"
    print sys.argv[0] + " usage:"
    print sys.argv[0] + "{get|set|reset} {command} [parameter]"
    print ""
    print "get   - Retrieves information from the monitor"
    print "set   - Sets a value in the monitor"
    print "reset - Resets a monitor capability"
    print ""
    print " parameter is required only for set commands"
    print ""
    print "get commands:"
    print "    assettag, monitorname, monitorserial, backlighthours"
    print "    powerstate, powerled, powerusb"
    print "    brightness, contrast, aspectratio, sharpness"
    print "    inputcolorformat, colorpresetcaps, colorpreset, customcolor"
    print "    autoselect, videoinputcaps, videoinput"
    print "    pxpmode, pxpsubinput, pxplocation"
    print "    osdtransparency, osdlanguage, osdtimer, osdbuttonlock"
    print "    versionfirmware, ddcci, lcdconditioning"
    print ""
    print "set commands:"
    print "    powerstate, powerled, powerusb"
    print "    brightness, contrast, aspectratio, sharpness"
    print "    inputcolorformat, colorpreset, customcolor"
    print "    autoselect, videoinput"
    print "       Video Input Names:"
    print "           vga, dp, mdp, hdmi1, hdmi2"
    print "    pxpmode, pxpsubinput, pxplocation"
    print "       PxP modes:"
    print "           4k:        3840x2160 full screen"
    print "           smallPip:  3840x2160 full screen (primary video input)"
    print "                      small inset picture-in-picture"
    print "           bigPip:    3840x2160 full screen (primary video input)"
    print "                      large inset picture-in-picture"
    print "           4x4:       four 1920x1080 panes"
    print "           1x2:       one 3840x1080 window over 2x 1920x1080"
    print "           2x1:       one 1920x2160 window right of 2x 1920x1080"
    print "           SxS:       two 1920x2160 panes"
    print "       PiP Locations:"
    print "           topRight, topLeft, bottomRight, bottomLeft"
    print "    osdtransparency, osdlanguage, osdtimer, osdbuttonlock"
    print "       OSD Languages:"
    print "           english, spanish, french, german, portugese,"
    print "           russian, chinese, japanese"
    print "    ddcci, lcdconditioning"
    print ""
    print "reset commands:"
    print "    power, color, osd, factory"

def dump_info():
    commands = ["monitorname", "monitorserial", "backlighthours", "powerstate", "powerled", "powerusb", "brightness", "contrast", "aspectratio", "sharpness", "inputcolorformat", "colorpresetcaps", "colorpreset", "customcolor", "autoselect", "videoinputcaps", "videoinput", "pxpmode", "pxpsubinput", "pxplocation", "osdtransparency", "osdlanguage", "osdtimer", "osdbuttonlock", "versionfirmware", "ddcci", "lcdconditioning"]

    for command in commands:
        if (command == "pxpsubinput"):
            for index in range(0,4):
                p4317q_handle_command("get", command, index)
        else:
            param = None
            if (command == "customcolor"):
                param = 0
            p4317q_handle_command("get", command, param)


def p4317q_hex_format(message):
    "Create a hex-ascii string representation of message"
    hex = binascii.b2a_hex(message)
    formatted_hex = ':'.join(hex[i:i+2] for i in range(0, len(hex), 2))
    return formatted_hex

def p4317q_checksum(message, begin, length):
    "Calculate the single byte checksum of the input data"
    total = 0 
    for index in range(begin,begin+length):
        #total += message[index]
        total ^= message[index]
        #total &= 0xFF
        print_debug("DB:  total ^ 0x" + p4317q_hex_format(bytearray([message[index]])) + " = 0x" + p4317q_hex_format(bytearray([total&0xff])))
    total &= 0xFF
    print_debug("DB:  " + str(total)+ " 0x" + p4317q_hex_format(bytearray([total])))
    # Compute 2's complement of the sum.  Comment out if this isn't needed
    # total = (~total+1) & 0xFF
    print_debug("DB:  " + str(total)+ " 0x" + p4317q_hex_format(bytearray([total])))
    return total

#0x6E, 0x51, 0x02, 0xEB, 0x01, D7p

def p4317q_build_command(action, value, param):
    "Build a command to be sent to the monitor.  Assumed that param is a bytearray of the correct length"
    cmd_tag = (ACTIONS_MAP[action])[value]
    cmd_len = (ACTIONS_MAP[action])[value+"_len"]

    print_debug("DEBUG:  Param is [" + str(param) + "].  Type is [" + str(type(param)) + "].")
    command = CMD_HEADER + bytearray([cmd_len])
    if (action == "set"):
        cmd_act = CMD_WRITE
        command = command + bytearray([cmd_act]) + bytearray([cmd_tag])
        if (isinstance(param, bytearray)):
            command += param
        else:
            command += bytearray([param])
    else:
        cmd_act = CMD_READ
        command = command + bytearray([cmd_act]) + bytearray([cmd_tag])
        if (param is not None): command += bytearray([param])

    # compute the checksum and add that to the end
    # checksum = p4317q_checksum(command, 2, cmd_len+1)
    checksum = p4317q_checksum(command, 0, cmd_len+3)
    command = command + bytearray([checksum])
    return command

def p4317q_send_command(ser_port, command):
    ser_port.write(command)

def p4317q_parse_response(response, command):
    response_data = bytearray(response)
    # Create an additional buffer with the header in it for the new checksum:
    response_with_header = bytearray(response)
    response_payload_bytes = len(response_data) - 1
    print_debug("DEBUG: Response length is " + str(response_payload_bytes))
    response_with_header.insert(0, response_payload_bytes)
    response_with_header.insert(0, 0x37)
    response_with_header.insert(0, 0x6f)

    hex = p4317q_hex_format(bytearray([command]))
    print_debug("Parsing response.  Expecting command [" + hex + "].")
    # print_debug("Response data:\n    " + p4317q_hex_format(response_data))
    print_debug("Response data:\n    " + p4317q_hex_format(response_with_header))
    print_debug("Verifying checksum.")
    # ckdata = bytearray([len(response_data)-1]) + response_data
    # ckdata = bytearray([len(response_with_header)-1]) + response_with_header
    #chksum = p4317q_checksum(response_data,0,len(response_data)-1)
    # chksum = p4317q_checksum(ckdata,0,len(ckdata)-1)

    # chksum = p4317q_checksum(response_data,0,len(response_data)-1)
    # MC104 requires the checksum to be calculated with the header included
    # for both commands and responses:
    chksum = p4317q_checksum(response_with_header,0,len(response_with_header)-1)
    if (chksum != response_data[len(response_data)-1]):
        print_debug("ERROR.  CheckSum does not verify.  Calculated == " + p4317q_hex_format(bytearray([chksum])) + ".")
        # Checksum verification doesn't seem to matter (or work)
        return None
    else:
        print_debug("Checksum verified.")

    if (response_data[0] != RSP_REPLY_CODE):
        print "ERROR.  Reply code incorrect."
        return None
    print_debug("Result code = " + p4317q_hex_format(bytearray([response_data[1]])))
    # Probably could do with some operation on the result code here...

    if (response_data[2] != command):
        print_debug("DEBUG " + str(response_data[2]) + " == " + str(command) + ".")
        print "ERROR.  Received incorrect command response."
        return None
    else:
        print_debug("Command response is correct.")
    print_debug("Response Data:        " + p4317q_hex_format(response_data[3:-1]))
    if (command in (CMD_G_MONITOR_NAME_C, CMD_G_ASSET_TAG_C, CMD_G_MONITOR_SERIAL_C, CMD_G_VERSION_FIRMWARE_C)):
        print_debug("ASCII Response Data:  " + response_data[3:-1])
    print_debug("Done parsing.")
    return response_data[3:-1]

def p4317q_read_response(ser_port):
    # Read 2 bytes, make sure they're == RSP_HEADER
    resp_header = ser_port.read(2)
    print_debug("DEBUG:  Response header received has " + str(len(resp_header)) + " bytes.")
    print_debug("DEBUG:  Received response header = [" + p4317q_hex_format(resp_header) + "]")
    print_debug("DEBUG:  Expected response header = [" + p4317q_hex_format(RSP_HEADER) + "]")
    if (ord(resp_header[0]) != RSP_HEADER[0]):
        print_debug(str(ord(resp_header[0])) + " == " + str(RSP_HEADER[0]))
        print_debug("DEBUG:  1st byte of response header does not match " + p4317q_hex_format(RSP_HEADER))
        return None

    if (ord(resp_header[1]) != RSP_HEADER[1]):
        print_debug("DEBUG:  2nd byte of response header does not match " + p4317q_hex_format(RSP_HEADER))
        return None

    # Read 1 byte of len
    resp_len = ord(ser_port.read(1))
    print_debug("DEBUG:  Received data length of " + str(resp_len))
    # Read resp_len+1 bytes (message + checksum)
    response = ser_port.read(resp_len+1)
    return response

def p4317q_handle_command(action, command, param):
    cmd = p4317q_build_command(action, command, param)
    print_debug("DEBUG:  Command:  [" + p4317q_hex_format(cmd) + "]")

    # port = serial.Serial("COM3")
    port = serial.Serial("COM3", baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=None, xonxoff=0, rtscts=0)

    p4317q_send_command(port, cmd)

    response = p4317q_read_response(port)

    port.close()

    if (response is not None):
        print_debug("Response = [" + p4317q_hex_format(response) + "]")
        parsedResponse = p4317q_parse_response(response, (ACTIONS_MAP[action])[command])

    if (parsedResponse is not None and action == "get"):
        format_response(command, parsedResponse, param)


def format_response(command, response, param):
    if   (command == "assettag"):
        print ""
    elif (command == "monitorname"):
        print "Monitor Name         = " + str(response)
    elif (command == "monitorserial"):
        print "Monitor Serial #     = " + str(response)
    elif (command == "backlighthours"):
        print "Backlight Hours      = " + str(struct.unpack("<h", response)[0])
    elif (command == "powerstate"):
        print "Power State          = " + ("ON" if response[0]==1 else "OFF")
    elif (command == "powerled"):
        print "Power LED            = " + ("ON" if response[0]==1 else "OFF")
    elif (command == "powerusb"):
        print "Power USB            = " + ("ON" if response[0]==1 else "OFF")
    elif (command == "brightness"):
        print "Brightness           = " + str(response[0])
    elif (command == "contrast"):
        print "Contrast             = " + str(response[0])
    elif (command == "aspectratio"):
        ratios = { v: k for k, v in aspect_ratios.items() }
        print "Aspect Ratio         = " + ratios[response[0]]
    elif (command == "sharpness"):
        print "Sharpness            = " + str(response[0])
    elif (command == "inputcolorformat"):
        formats = { v: k for k, v in input_color_formats.items() }
        print "Input Color Format   = " + formats[response[0]]
    elif (command == "colorpresetcaps"):
        print "Color Preset Caps    = " + p4317q_hex_format(response)
    elif (command == "colorpreset"):
        print "Color Preset         = " + color_preset_inv[struct.unpack("<h", response[0:2])[0]]
    elif (command == "customcolor"):
        print "Custom Color [R:G:B] = [" + str(response[0]) + ":" + str(response[1]) + ":" + str(response[2]) + "]"
    elif (command == "autoselect"):
        print "Input Auto Select    = " + ("ON" if response[0]==1 else "OFF")
    elif (command == "videoinputcaps"):
        print "Video Input Caps     = " + p4317q_hex_format(response)
    elif (command == "videoinput"):
        inputs = { v[0]: k for k, v in pxp_input.items() }
        print "Video Input          = " + inputs[int(response[0])]
    elif (command == "pxpmode"):
        modes = { v: k for k, v in pxp_mode.items() }
        print "PxP/PiP Mode         = " + modes[response[0]]
    elif (command == "pxpsubinput"):
        inputs = { v[0]: k for k, v in pxp_input.items() }
        print "PxP/PiP Sub Input[" + str(param+1) + "] = " + inputs[int(response[0])]
    elif (command == "pxplocation"):
        locations = { v: k for k, v in pxp_locations.items() }
        print "PiP Window Location  = " + locations[int(response[0])]
    elif (command == "osdtransparency"):
        print "OSD Transparency     = " + str(response[0])
    elif (command == "osdlanguage"):
        languages = { v: k for k, v in osd_language.items() }
        print "OSD Language         = " + languages[int(response[0])]
    elif (command == "osdtimer"):
        print "OSD Timer            = " + str(response[0])
    elif (command == "osdbuttonlock"):
        print "OSD Button Lock      = " + ("ON" if response[0]==1 else "OFF")
    elif (command == "versionfirmware"):
        print "Firmware Version     = " + response
    elif (command == "ddcci"):
        print "DDC/CI               = " + ("ON" if response[0]==1 else "OFF")
    elif (command == "lcdconditioning"):
        print "LCD Conditioning     = " + ("ON" if response[0]==1 else "OFF")
    return


# MONITOR MANAGEMENT
CMD_G_ASSET_TAG_L=0x02
CMD_G_ASSET_TAG_C=0x00
CMD_G_ASSET_TAG_RESP_L=0x0D
CMD_G_MONITOR_NAME_L=0x02
CMD_G_MONITOR_NAME_C=0x01
CMD_G_MONITOR_NAME_RESP_L=0x0D
CMD_G_MONITOR_SERIAL_L=0x02
CMD_G_MONITOR_SERIAL_C=0x02
CMD_G_MONITOR_SERIAL_RESP_L=0x0D
CMD_G_BACKLIGHT_HOURS_L=0x02
CMD_G_BACKLIGHT_HOURS_C=0x04
CMD_G_BACKLIGHT_HOURS_RESP_L=0x05

# POWER MANAGEMENT
CMD_G_POWER_STATE_L=0x02
CMD_G_POWER_STATE_C=0x20
CMD_G_POWER_STATE_RESP_L=0x04
CMD_S_POWER_STATE_L=0x03
CMD_S_POWER_STATE_C=0x20
CMD_G_POWER_LED_L=0x02
CMD_G_POWER_LED_C=0x21
CMD_G_POWER_LED_RESP_L=0x04
CMD_S_POWER_LED_L=0x03
CMD_S_POWER_LED_C=0x21
CMD_G_POWER_USB_L=0x02
CMD_G_POWER_USB_C=0x22
CMD_G_POWER_USB_RESP_L=0x04
CMD_S_POWER_USB_L=0x03
CMD_S_POWER_USB_C=0x22
CMD_RESET_POWER_L=0x02
CMD_RESET_POWER_C=0x2F

# IMAGE ADJUSTMENT
CMD_G_BRIGHTNESS_L=0x02
CMD_G_BRIGHTNESS_C=0x30
CMD_G_BRIGHTNESS_RESP_L=0x04
CMD_S_BRIGHTNESS_L=0x03
CMD_S_BRIGHTNESS_C=0x30
CMD_G_CONTRAST_L=0x02
CMD_G_CONTRAST_C=0x31
CMD_G_CONTRAST_RESP_L=0x04
CMD_S_CONTRAST_L=0x03
CMD_S_CONTRAST_C=0x31
CMD_G_ASPECT_RATIO_L=0x02
CMD_G_ASPECT_RATIO_C=0x33
CMD_G_ASPECT_RATIO_RESP_L=0x04
CMD_S_ASPECT_RATIO_L=0x03
CMD_S_ASPECT_RATIO_C=0x33
CMD_G_SHARPNESS_L=0x02
CMD_G_SHARPNESS_C=0x34
CMD_G_SHARPNESS_RESP_L=0x04
CMD_S_SHARPNESS_L=0x03
CMD_S_SHARPNESS_C=0x34

aspect_ratios = { "16x9": 0,
                  "4x3":  2,
                  "5x4":  4 }

# COLOR MANAGEMENT
CMD_G_INPUT_COLOR_FORMAT_L=0x02
CMD_G_INPUT_COLOR_FORMAT_C=0x46
CMD_G_INPUT_COLOR_FORMAT_RESP_L=0x04
CMD_S_INPUT_COLOR_FORMAT_L=0x03
CMD_S_INPUT_COLOR_FORMAT_C=0x46
CMD_G_COLOR_PRESET_CAPS_L=0x02
CMD_G_COLOR_PRESET_CAPS_C=0x47
CMD_G_COLOR_PRESET_CAPS_RESP_L=0x07
CMD_G_COLOR_PRESET_L=0x02
CMD_G_COLOR_PRESET_C=0x48
CMD_G_COLOR_PRESET_RESP_L=0x07
CMD_S_COLOR_PRESET_L=0x06
CMD_S_COLOR_PRESET_C=0x48
CMD_G_CUSTOM_COLOR_L=0x03
CMD_G_CUSTOM_RESP_L=0x09
CMD_G_CUSTOM_COLOR_C=0x49
CMD_G_CUSTOM_COLOR_RESP_L=0x09
CMD_S_CUSTOM_COLOR_L=0x09
CMD_S_CUSTOM_COLOR_C=0x49
CMD_RESET_COLOR_L=0x02
CMD_RESET_COLOR_C=0x4F

input_color_formats = { "RGB": 0,
                        "YPbPr": 1 }

color_presets = { "standard": bytearray([0x01, 0x00, 0x00, 0x00]),
                  "paper":    bytearray([0x10, 0x00, 0x00, 0x00]),
                  "warm":     bytearray([0x00, 0x01, 0x00, 0x00]),
                  "cool":     bytearray([0x00, 0x02, 0x00, 0x00]),
                  "custom":   bytearray([0x80, 0x00, 0x00, 0x00]) }
color_preset_inv = { struct.unpack("<h", bytearray([0x01, 0x00]))[0]:  "standard",
                     struct.unpack("<h", bytearray([0x10, 0x00]))[0]:  "paper",
                     struct.unpack("<h", bytearray([0x00, 0x01]))[0]:  "warm",
                     struct.unpack("<h", bytearray([0x00, 0x02]))[0]:  "cool",
                     struct.unpack("<h", bytearray([0x80, 0x00]))[0]:  "custom" }

# VIDEO INPUT MANAGEMENT
CMD_G_AUTO_SELECT_L=0x02
CMD_G_AUTO_SELECT_C=0x60
CMD_G_AUTO_SELECT_RESP_L=0x04
CMD_S_AUTO_SELECT_L=0x03
CMD_S_AUTO_SELECT_C=0x60
CMD_G_VIDEO_INPUT_CAPS_L=0x02
CMD_G_VIDEO_INPUT_CAPS_C=0x61
CMD_G_VIDEO_INPUT_CAPS_RESP_L=0x07
CMD_G_VIDEO_INPUT_L=0x02
CMD_G_VIDEO_INPUT_C=0x62
CMD_G_VIDEO_INPUT_RESP_L=0x07
CMD_S_VIDEO_INPUT_L=0x06
CMD_S_VIDEO_INPUT_C=0x62

# PIP/PBP MANAGEMENT
CMD_G_PXP_MODE_L=0x02
CMD_G_PXP_MODE_C=0x70
CMD_G_PXP_MODE_RESP_L=0x04
CMD_S_PXP_MODE_L=0x03
CMD_S_PXP_MODE_C=0x70
CMD_G_PXP_SUBINPUT_L=0x03
CMD_G_PXP_SUBINPUT_C=0x71
CMD_G_PXP_SUBINPUT_RESP_L=0x07
CMD_S_PXP_SUBINPUT_L=0x07
CMD_S_PXP_SUBINPUT_C=0x71
CMD_G_PXP_LOCATION_L=0x02
CMD_G_PXP_LOCATION_C=0x72
CMD_G_PXP_LOCATION_RESP_L=0x04
CMD_S_PXP_LOCATION_L=0x03
CMD_S_PXP_LOCATION_C=0x72

pxp_mode = { "4k": 0,
             "smallPip": 1,
             "bigPip": 2,
             "SxS": 3,
             "stretchSxS": 4,
             "2x1": 6,
             "1x2": 7,
             "4x4": 8 }

pxp_input = { "vga":   bytearray([0x40, 0x00, 0x00, 0x00]),
              "dp":    bytearray([0x08, 0x00, 0x00, 0x00]),
              "mdp":   bytearray([0x10, 0x00, 0x00, 0x00]),
              "hdmi1": bytearray([0x01, 0x00, 0x00, 0x00]),
              "hdmi2": bytearray([0x02, 0x00, 0x00, 0x00]) }

pxp_locations = { "topRight": 0,
                  "topLeft": 1,
                  "bottomRight": 2,
                  "bottomLeft": 3 }
# PxP Locations (PiP Location)
# 0 - Top Right
# 1 - Top Left
# 2 - Bottom Right
# 3 - Bottom Left

# OSD MANAGEMENT
CMD_S_OSD_TRANSPARENCY_L=0x03
CMD_S_OSD_TRANSPARENCY_C=0x80
CMD_G_OSD_TRANSPARENCY_L=0x02
CMD_G_OSD_TRANSPARENCY_C=0x80
CMD_G_OSD_TRANSPARENCY_RESP_L=0x04
CMD_S_OSD_LANGUAGE_L=0x03
CMD_S_OSD_LANGUAGE_C=0x81
CMD_G_OSD_LANGUAGE_L=0x02
CMD_G_OSD_LANGUAGE_C=0x81
CMD_G_OSD_LANGUAGE_RESP_L=0x04
CMD_S_OSD_TIMER_L=0x03
CMD_S_OSD_TIMER_C=0x83
CMD_G_OSD_TIMER_L=0x02
CMD_G_OSD_TIMER_C=0x83
CMD_G_OSD_TIMER_RESP_L=0x04
CMD_S_OSD_BUTTON_LOCK_L=0x03
CMD_S_OSD_BUTTON_LOCK_C=0x84
CMD_G_OSD_BUTTON_LOCK_L=0x02
CMD_G_OSD_BUTTON_LOCK_C=0x84
CMD_G_OSD_BUTTON_LOCK_RESP_L=0x04
CMD_RESET_OSD_L=0x02
CMD_RESET_OSD_C=0x8F

osd_language = { "english": 0,
                 "spanish": 1,
                 "french": 2,
                 "german": 3,
                 "portugese": 4,
                 "russian": 5,
                 "chinese": 6,
                 "japanese": 7 }
# OSD Languages
# 0 - English
# 1 - Spanish
# 2 - French
# 3 - German
# 4 - Portugese
# 5 - Russian
# 6 - Chinese ?
# 7 - Japanese ?

# SYSTEM MANAGEMENT
CMD_G_VERSION_FIRMWARE_L=0x02
CMD_G_VERSION_FIRMWARE_C=0xA0
CMD_G_VERSION_FIRMWARE_RESP_L=0x05
CMD_G_DDCCI_L=0x02
CMD_G_DDCCI_C=0xA2
CMD_G_DDCCI_RESP_L=0x04
CMD_S_DDCCI_L=0x03
CMD_S_DDCCI_C=0xA2
CMD_G_LCD_CONDITIONING_L=0x02
CMD_G_LCD_CONDITIONING_C=0xA3
CMD_G_LCD_CONDITIONING_RESP_L=0x04
CMD_S_LCD_CONDITIONING_L=0x03
CMD_S_LCD_CONDITIONING_C=0xA3
CMD_FACTORY_RESET_L=0x02
CMD_FACTORY_RESET_C=0xAF

GET_ACTIONS = {
    "assettag": CMD_G_ASSET_TAG_C                  , "assettag_len": CMD_G_ASSET_TAG_L,
    "assettag_resplen": CMD_G_ASSET_TAG_RESP_L,
    "monitorname": CMD_G_MONITOR_NAME_C            , "monitorname_len": CMD_G_MONITOR_NAME_L,
    "monitorname_resplen": CMD_G_MONITOR_NAME_RESP_L,
    "monitorserial": CMD_G_MONITOR_SERIAL_C        , "monitorserial_len": CMD_G_MONITOR_SERIAL_L,
    "monitorserial_resplen": CMD_G_MONITOR_SERIAL_RESP_L,
    "backlighthours": CMD_G_BACKLIGHT_HOURS_C      , "backlighthours_len": CMD_G_BACKLIGHT_HOURS_L,
    "backlighthours_resplen": CMD_G_BACKLIGHT_HOURS_RESP_L,
    "powerstate": CMD_G_POWER_STATE_C              , "powerstate_len": CMD_G_POWER_STATE_L,
    "powerstate_resplen": CMD_G_POWER_STATE_RESP_L,
    "powerled": CMD_G_POWER_LED_C                  , "powerled_len": CMD_G_POWER_LED_L,
    "powerled_resplen": CMD_G_POWER_LED_RESP_L,
    "powerusb": CMD_G_POWER_USB_C                  , "powerusb_len": CMD_G_POWER_USB_L,
    "powerusb_resplen": CMD_G_POWER_USB_RESP_L,
    "brightness": CMD_G_BRIGHTNESS_C               , "brightness_len": CMD_G_BRIGHTNESS_L,
    "brightness_resplen": CMD_G_BRIGHTNESS_RESP_L,
    "contrast": CMD_G_CONTRAST_C                   , "contrast_len": CMD_G_CONTRAST_L,
    "contrast_resplen": CMD_G_CONTRAST_RESP_L,
    "aspectratio": CMD_G_ASPECT_RATIO_C            , "aspectratio_len": CMD_G_ASPECT_RATIO_L,
    "aspectratio_resplen": CMD_G_ASPECT_RATIO_RESP_L,
    "sharpness": CMD_G_SHARPNESS_C                 , "sharpness_len": CMD_G_SHARPNESS_L,
    "sharpness_resplen": CMD_G_SHARPNESS_RESP_L,
    "inputcolorformat": CMD_G_INPUT_COLOR_FORMAT_C , "inputcolorformat_len": CMD_G_INPUT_COLOR_FORMAT_L,
    "inputcolorformat_resplen": CMD_G_INPUT_COLOR_FORMAT_RESP_L,
    "colorpresetcaps": CMD_G_COLOR_PRESET_CAPS_C   , "colorpresetcaps_len": CMD_G_COLOR_PRESET_CAPS_L,
    "colorpresetcaps_resplen": CMD_G_COLOR_PRESET_CAPS_RESP_L,
    "colorpreset": CMD_G_COLOR_PRESET_C            , "colorpreset_len": CMD_G_COLOR_PRESET_L,
    "colorpreset_resplen": CMD_G_COLOR_PRESET_RESP_L,
    "customcolor": CMD_G_CUSTOM_COLOR_C            , "customcolor_len": CMD_G_CUSTOM_COLOR_L,
    "customcolor_resplen": CMD_G_CUSTOM_COLOR_RESP_L,
    "autoselect": CMD_G_AUTO_SELECT_C              , "autoselect_len": CMD_G_AUTO_SELECT_L,
    "autoselect_resplen": CMD_G_AUTO_SELECT_RESP_L,
    "videoinputcaps": CMD_G_VIDEO_INPUT_CAPS_C     , "videoinputcaps_len": CMD_G_VIDEO_INPUT_CAPS_L,
    "videoinputcaps_resplen": CMD_G_VIDEO_INPUT_CAPS_RESP_L,
    "videoinput": CMD_G_VIDEO_INPUT_C              , "videoinput_len": CMD_G_VIDEO_INPUT_L,
    "videoinput_resplen": CMD_G_VIDEO_INPUT_RESP_L,
    "pxpmode": CMD_G_PXP_MODE_C                    , "pxpmode_len": CMD_G_PXP_MODE_L,
    "pxpmode_resplen": CMD_G_PXP_MODE_RESP_L,
    "pxpsubinput": CMD_G_PXP_SUBINPUT_C            , "pxpsubinput_len": CMD_G_PXP_SUBINPUT_L,
    "pxpsubinput_resplen": CMD_G_PXP_SUBINPUT_RESP_L,
    "pxplocation": CMD_G_PXP_LOCATION_C            , "pxplocation_len": CMD_G_PXP_LOCATION_L,
    "pxplocation_resplen": CMD_G_PXP_LOCATION_RESP_L,
    "osdtransparency": CMD_G_OSD_TRANSPARENCY_C    , "osdtransparency_len": CMD_G_OSD_TRANSPARENCY_L,
    "osdtransparency_resplen": CMD_G_OSD_TRANSPARENCY_RESP_L,
    "osdlanguage": CMD_G_OSD_LANGUAGE_C            , "osdlanguage_len": CMD_G_OSD_LANGUAGE_L,
    "osdlanguage_resplen": CMD_G_OSD_LANGUAGE_RESP_L,
    "osdtimer": CMD_G_OSD_TIMER_C                  , "osdtimer_len": CMD_G_OSD_TIMER_L,
    "osdtimer_resplen": CMD_G_OSD_TIMER_RESP_L,
    "osdbuttonlock": CMD_G_OSD_BUTTON_LOCK_C       , "osdbuttonlock_len": CMD_G_OSD_BUTTON_LOCK_L,
    "osdbuttonlock_resplen": CMD_G_OSD_BUTTON_LOCK_RESP_L,
    "versionfirmware": CMD_G_VERSION_FIRMWARE_C    , "versionfirmware_len": CMD_G_VERSION_FIRMWARE_L,
    "versionfirmware_resplen": CMD_G_VERSION_FIRMWARE_RESP_L,
    "ddcci": CMD_G_DDCCI_C                         , "ddcci_len": CMD_G_DDCCI_L,
    "ddcci_resplen": CMD_G_DDCCI_RESP_L,
    "lcdconditioning": CMD_G_LCD_CONDITIONING_C    , "lcdconditioning_len": CMD_G_LCD_CONDITIONING_L,
    "lcdconditioning_resplen": CMD_G_LCD_CONDITIONING_RESP_L
}

SET_ACTIONS = {
    "powerstate": CMD_S_POWER_STATE_C              , "powerstate_len": CMD_S_POWER_STATE_L,
    "powerled": CMD_S_POWER_LED_C                  , "powerled_len": CMD_S_POWER_LED_L,
    "powerusb": CMD_S_POWER_USB_C                  , "powerusb_len": CMD_S_POWER_USB_L,
    "brightness": CMD_S_BRIGHTNESS_C               , "brightness_len": CMD_S_BRIGHTNESS_L,
    "contrast": CMD_S_CONTRAST_C                   , "contrast_len": CMD_S_CONTRAST_L,
    "aspectratio": CMD_S_ASPECT_RATIO_C            , "aspectratio_len": CMD_S_ASPECT_RATIO_L,
    "sharpness": CMD_S_SHARPNESS_C                 , "sharpness_len": CMD_S_SHARPNESS_L,
    "inputcolorformat": CMD_S_INPUT_COLOR_FORMAT_C , "inputcolorformat_len": CMD_S_INPUT_COLOR_FORMAT_L,
    "colorpreset": CMD_S_COLOR_PRESET_C            , "colorpreset_len": CMD_S_COLOR_PRESET_L,
    "customcolor": CMD_S_CUSTOM_COLOR_C            , "customcolor_len": CMD_S_CUSTOM_COLOR_L,
    "autoselect": CMD_S_AUTO_SELECT_C              , "autoselect_len": CMD_S_AUTO_SELECT_L,
    "videoinput": CMD_S_VIDEO_INPUT_C              , "videoinput_len": CMD_S_VIDEO_INPUT_L,
    "pxpmode": CMD_S_PXP_MODE_C                    , "pxpmode_len": CMD_S_PXP_MODE_L,
    "pxpsubinput": CMD_S_PXP_SUBINPUT_C            , "pxpsubinput_len": CMD_S_PXP_SUBINPUT_L,
    "pxplocation": CMD_S_PXP_LOCATION_C            , "pxplocation_len": CMD_S_PXP_LOCATION_L,
    "osdtransparency": CMD_S_OSD_TRANSPARENCY_C    , "osdtransparency_len": CMD_S_OSD_TRANSPARENCY_L,
    "osdlanguage": CMD_S_OSD_LANGUAGE_C            , "osdlanguage_len": CMD_S_OSD_LANGUAGE_L,
    "osdtimer": CMD_S_OSD_TIMER_C                  , "osdtimer_len": CMD_S_OSD_TIMER_L,
    "osdbuttonlock": CMD_S_OSD_BUTTON_LOCK_C       , "osdbuttonlock_len": CMD_S_OSD_BUTTON_LOCK_L,
    "ddcci": CMD_S_DDCCI_C                         , "ddcci_len": CMD_S_DDCCI_L,
    "lcdconditioning": CMD_S_LCD_CONDITIONING_C    , "lcdconditioning_len": CMD_S_LCD_CONDITIONING_L
}

RESET_ACTIONS = {
    "power": CMD_RESET_POWER_C                     , "power_len": CMD_RESET_POWER_L,
    "color": CMD_RESET_COLOR_C                     , "color_len": CMD_RESET_COLOR_L,
    "osd": CMD_RESET_OSD_C                         , "osd_len": CMD_RESET_OSD_L,
    "factory": CMD_FACTORY_RESET_C                 , "factory_len": CMD_FACTORY_RESET_L
}

ACTIONS_MAP = { "get": GET_ACTIONS, "set": SET_ACTIONS, "reset": RESET_ACTIONS }

print_debug("len(sys.argv) = " + str(len(sys.argv)))
print_debug("args = " + str(sys.argv))
if (len(sys.argv) < 2 or len(sys.argv) > 5):
    print_usage()
    exit()

if (sys.argv[1] == "dump"):
    dump_info()
    exit()

if (sys.argv[1] in ("get", "set", "reset")):
    keys = ACTIONS_MAP[sys.argv[1]].keys()
    if (sys.argv[2] not in keys):
        print "ERROR:  Invalid command specified"
        exit()
else:
    print "ERROR:  Invalid action specified"
    exit()

param = None
if (len(sys.argv) >= 4):
    if (sys.argv[1] == "set"):
        if   (sys.argv[2] == "osdlanguage"):
            param = osd_language[sys.argv[3]]
        elif (sys.argv[2] == "pxplocation"):
            param = pxp_locations[sys.argv[3]]
        elif (sys.argv[2] == "pxpmode"):
            param = pxp_mode[sys.argv[3]]
        elif (sys.argv[2] == "videoinput"):
            param = pxp_input[sys.argv[3]]
        elif (sys.argv[2] == "pxpsubinput"):
            print "pxpsubinput"
            param = bytearray([int(sys.argv[3])-1])
            param += pxp_input[sys.argv[4]]
            print "param:  " + p4317q_hex_format(param)
        else:
            param = int(sys.argv[3])
    else:
        param = int(sys.argv[3])

output = p4317q_handle_command(sys.argv[1], sys.argv[2], param)
