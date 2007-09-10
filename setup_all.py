#!/usr/bin/python

# Copyright (C) 2006, Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

from sugar.activity import bundlebuilder
import os
import shutil

os.rename('activity/activity.info', 'activity/activity_old.info')
shutil.copyfile('activity/activity_sl.info', 'activity/activity.info')
bundlebuilder.start('TamTamSynthLab')
os.rename('activity/activity_old.info', 'activity/activity.info')

os.rename('activity/activity.info', 'activity/activity_old.info')
shutil.copyfile('activity/activity_mini.info', 'activity/activity.info')
bundlebuilder.start('TamTamMini')
os.rename('activity/activity_old.info', 'activity/activity.info')

os.rename('activity/activity.info', 'activity/activity_old.info')
shutil.copyfile('activity/activity_jam.info', 'activity/activity.info')
bundlebuilder.start('TamTamJam')
os.rename('activity/activity_old.info', 'activity/activity.info')

os.rename('activity/activity.info', 'activity/activity_old.info')
shutil.copyfile('activity/activity_edit.info', 'activity/activity.info')
bundlebuilder.start('TamTamEdit')
os.rename('activity/activity_old.info', 'activity/activity.info')