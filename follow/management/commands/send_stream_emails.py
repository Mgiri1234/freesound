#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#
from django.core.mail import send_mass_mail
from django.core.management.base import BaseCommand
from django.conf import settings
from utils.mail import render_mail_template
from accounts.models import Profile
import datetime
from follow import follow_utils
from django.contrib.auth.models import User


class Command(BaseCommand):
    '''
    This command should be run periodically several times a day, and it will only send emails to users that "require it"
    '''
    args = ''
    help = 'Send stream notifications to users who have not been notified for the last settings.NOTIFICATION_TIMEDELTA_PERIOD period and whose stream has new sounds for that period'

    def handle(self, *args, **options):

        date_today_minus_notification_timedelta = datetime.datetime.now() - settings.NOTIFICATION_TIMEDELTA_PERIOD

        # Get all the users that have notifications active
        # and exclude the ones that have the last email sent for less than settings.NOTIFICATION_TIMEDELTA_PERIOD
        # (because they have been sent an email already)
        users_enabled_notifications = Profile.objects.filter(enabled_stream_emails=True).exclude(last_stream_email_sent__gt=date_today_minus_notification_timedelta).order_by("last_stream_email_sent")[:settings.MAX_EMAILS_PER_COMMAND_RUN]

        print "Checking new sounds for", len(users_enabled_notifications), "users"
        print [str(profile.user.username) for profile in users_enabled_notifications]

        email_tuples = ()

        for profile in users_enabled_notifications:

            username = profile.user.username
            email_to = profile.user.email

            # Variable names use the terminology "week" because settings.NOTIFICATION_TIMEDELTA_PERIOD defaults to a
            # week, but a more generic terminology could be used
            week_first_day = profile.last_stream_email_sent
            week_last_day = datetime.datetime.now()

            week_first_day_str = week_first_day.strftime("%d %b").lstrip("0")
            week_last_day_str = week_last_day.strftime("%d %b").lstrip("0")

            subject_str = u'new sounds from users you are following ('
            subject_str += unicode(week_first_day_str) + u' - ' + unicode(week_last_day_str) + u')'

            # Set date range from which to get upload notifications
            time_lapse = follow_utils.build_time_lapse(week_first_day, week_last_day)

            # construct message
            user = User.objects.get(username=username)
            users_sounds, tags_sounds = follow_utils.get_stream_sounds(user, time_lapse)

            if not users_sounds and not tags_sounds:
                print "no news sounds for", username
                continue

            # print users_sound_ids
            # print tags_sound_ids

            text_content = render_mail_template('follow/email_stream.txt', locals())

            email_tuples += (subject_str, text_content, settings.DEFAULT_FROM_EMAIL, [email_to]),

            # update last stream email sent date
            profile.last_stream_email_sent = datetime.datetime.now()
            profile.save()

        # mass email all messages
        send_mass_mail(email_tuples, fail_silently=False)