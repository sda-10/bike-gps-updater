# Bike GPS Firmware Updater compatible with Bryton Rider 15 Neo (and maybe others)
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
#

import urllib.request, sys, os, configparser

# Add additional devices here once behavior is verified.
# No support is yet provided for map updates.
supported_devices = ['Rider15neo']

device_info_file = "System/device.txt"

update_url = "https://rexray-s3fs-jeff.s3.ap-northeast-1.amazonaws.com/mapdata/updatetool2/Device/{}/{}"

if len(sys.argv) < 2:
    print('usage: {} path_to_device [-force]'.format(sys.argv[0]))
    sys.exit(1)

device = sys.argv[1]

force_unsupported = False
if len(sys.argv) > 2:
    if sys.argv[2] == '-force':
        force_unsupported = True

if not os.path.exists(device):
    print('unable to open device "{}"'.format(device))
    sys.exit(1)

# Attempt to open the ini file
device_info_file_path = os.path.join(device, device_info_file)

if not os.path.exists(device_info_file_path):
    print('unable to open device info file "{}"'.format(device_info_file_path))
    sys.exit(1)

info_file_config = configparser.ConfigParser()
info_file_config.read(device_info_file_path)

device_sku = None

try:
    device_sku = info_file_config['MODEL']['model']
except:
    print("device info file missing MODEL / SKU")
    sys.exit(1)

print('device model "{}"'.format(device_sku))

if device_sku not in supported_devices:
    if force_unsupported:
        print('UNSUPPORTED DEVICE, CONTINUING WITH -force FLAG')
    else:
        print('this device is not supported by this tool')
        sys.exit(1)

release_url_device = update_url.format(device_sku, 'release.ini')
print('attempting to fetch update info from "{}"'.format(release_url_device))

update_info_raw = ''

try:
    with urllib.request.urlopen(release_url_device) as f:
        update_info_raw = f.read().decode('utf-8')
        f.close()
except:
    print('error downloading update info')
    sys.exit(1)

update_info_config = configparser.ConfigParser()
update_info_config.read_string(update_info_raw)

files_to_update = []

print('examining sections for updates:')
for section in update_info_config.sections():
    if 'Size' not in update_info_config[section]:
        continue

    if update_info_config[section]['Size'] == '0':
        print('\t"{}" not updateable (zero size)'.format(section))
        continue

    if section not in info_file_config.sections():
        print('found unknown section "{}" that is not already present on device, terminating'.format(section))
        sys.exit(1)

    if 'Version' not in update_info_config[section]:
        print('section "{}" locally missing Name field", terminating'.format(section))
        sys.exit(1)

    if 'Version' not in info_file_config[section]:
        print('section "{}" missing Name field", terminating'.format(section))
        sys.exit(1)

    if update_info_config[section]['Version'] == info_file_config[section]['Version']:
        print('\t"{}" version {} matches {}'.format(section, update_info_config[section]['Version'], info_file_config[section]['Version']))
        continue

    if 'Name' not in update_info_config[section]:
        print('section "{} missing Name field", terminating'.format(section))
        sys.exit(1)

    files_to_update.append((update_info_config[section]['Name'], section, update_info_config[section]['Version'], info_file_config[section]['Version'], int(update_info_config[section]['Size'])))

if len(files_to_update) == 0:
    print('nothing to do, exiting')
    sys.exit(1)

files_to_update.append(('update.ini', None, None, None, None))

print('will attempt to update the following files:')
for file in files_to_update:
    if file[1] is None:
        print('\t{}'.format(file[0]))
    else:
        print('\t{} ({} from {} to {}), {} bytes'.format(file[0], file[1], file[2], file[3], file[4]))

print('note that this might brick your device, and you do this ENTIRELY AT YOUR OWN RISK.')
c = input('proceed with update? (y/N)')
if c.strip() != 'y':
    sys.exit(0)

for file in files_to_update:
    file_url = update_url.format(device_sku, file[0])
    print('fetching "{}"'.format(file_url))

    try:
        file_raw = None
        with urllib.request.urlopen(file_url) as f:
            file_raw = f.read()
            f.close()


        if file[4] is not None and len(file_raw) != file[4]:
            print('retrieved non matching size {} expected {}'.format(len(file_raw), file[4]))
            sys.exit(1)

        dest_path = os.path.join(device, file[0])
        print('fetched {} bytes, writing to "{}"... THIS MAY TAKE SOME TIME'.format(len(file_raw), dest_path))

        with open(dest_path, 'wb') as fo:
            fo.write(file_raw)
            fo.close()

        print('finished writing file to device')

    except:
        print('error downloading update file')
        sys.exit(1)

print('updated files have been loaded on device. unplug device to start update.')
