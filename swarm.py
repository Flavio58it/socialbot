# Copyright (c) 2017 Isaac de la Pena (isaacdlp@alum.mit.edu)
#
# Open-sourced according to the MIT LICENSE
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


import sys, json, glob
from random import shuffle, choice
import socialbot
from time import sleep

bot_alias = "pack"
bot_type = "twitter"
action = "post"
param = None

if len(sys.argv) > 1:
    bot_alias = sys.argv[1]
    if len(sys.argv) > 2:
       bot_type = sys.argv[2]
       if len(sys.argv) > 3:
           action = sys.argv[3]
           if len(sys.argv) > 4:
               param = sys.argv[4]

basename = "%s-%s" % (bot_alias, bot_type)

# Gather credentials

siblings = glob.glob("%s-bots/*-bot.json" % basename)
shuffle(siblings)

if action == "fix":

    # Fix broken bots action

    for num, sibling in enumerate(siblings):

        with open(sibling, "r") as f:
            credentials = json.load(f)

        if credentials["status"] != "on":
            bot = socialbot.Twitter(log_name=basename)
            bot.pauses["action"] = lambda: 1
            bot.username = credentials["username"]

            try:
                bot.login(bot.username, credentials["password"])

                print("%i %s %s %s" % (num, bot.username, credentials["phone"], credentials["password"]))

                needs_phone = bot.wait_for("input#challenge_response", complain=False)
                if needs_phone is not None:
                    needs_phone.send_keys(credentials["phone"])
                    button = bot.wait_for("input#email_challenge_submit", complain=False)
                    button.submit()

                if bot.logged():
                    jar = bot.browser.get_cookies()
                    credentials["status"] = "on"
                    with open("%s-bots/%s-bot.json" % (basename, bot.username), "w") as f:
                        json.dump(credentials, f, indent=4)
                    with open("%s-bots/%s-cookie.json" % (basename, bot.username), "w") as f:
                        jar = bot.browser.get_cookies()
                        json.dump(jar, f, indent=4)
                    bot.quit()
                else:
                    print("Problem with %s" % bot.username)
            except:
                print("Failure with %s" % bot.username)

else:

    pack_size = 2
    if param is not None:
        pack_size = int(param)
    bots = []

    blacklist = []
    try:
        with open("%s-blacklist.json" % basename, "r") as f:
            blacklist = json.load(f)
    except:
        print("No blacklist found")

    for sibling in siblings:

        with open(sibling, "r") as f:
            credentials = json.load(f)

        if credentials["status"] == "on":
            bot = socialbot.Twitter(log_name=basename)
            bot.pauses["action"] = lambda: 1
            bot.username = credentials["username"]
            cookies = None
            try:
                with open("%s-bots/%s-cookie.json" % (basename, bot.username), "r") as f:
                    cookies = json.load(f)
            except:
                pass
            try:
                if cookies is None:
                    bot.login(bot.username, credentials["password"])
                else:
                    bot.set_cookies(cookies, bot_type)
                if bot.logged():
                    print("Adding %s to the pack" % bot.username)
                    bot.status = "on"
                    bots.append(bot)
                    if len(bots) >= pack_size:
                        break
            except Exception as ex:
                print("Issue %s with %s !" % (ex, bot.username))
                credentials["status"] = "off"
                with open("%s-bots/%s-bot.json" % (basename, bot.username), "w") as f:
                    json.dump(credentials, f, indent=4)
                bot.quit()

    try:

        if action == "post":

        # Post messages to targets action

            with open("%s-msgs.json" % (basename), "r") as f:
                msgs = json.load(f)

            with open("%s-targets.json" % (basename), "r") as f:
                targets = json.load(f)
            target_iter = iter(targets["@deck"])

            while(True):
                num = 0
                active = False
                for bot in bots:
                    try:
                        if bot.status == "on":
                            if bot.ready_to("post"):
                                try:
                                    target = None
                                    while target is None or target in blacklist:
                                        target = next(target_iter, False)
                                    msg = choice(msgs)
                                    msg = msg.replace("[handle]", "@%s" % target)
                                    bot.post(msg)
                                    print("%s posted '%s'" % (bot.username, msg))
                                    blacklist.append(target)
                                    num += 1
                                except StopIteration as ex:
                                    break
                            active = True
                    except Exception as ex:
                        bot.status = "off"
                        print("Failure %s with %s !" % (ex, bot.username))
                if not active:
                    print("No more bots working. Exiting.")
                    break
                if num < 1:
                    print("Too fast. Waiting.")
                    sleep(10)

    finally:
        with open("%s-blacklist.json" % basename, "w") as f:
            json.dump(list(set(blacklist)), f)
        for bot in bots:
            try:
                if bot.status == "off":
                    with open("%s-bots/%s-bot.json" % (basename, bot.username), "r") as f:
                        credentials = json.load(f)
                    credentials["status"] = "off"
                    with open("%s-bots/%s-bot.json" % (basename, bot.username), "w") as f:
                        json.dump(credentials, f, indent=4)
                with open("%s-bots/%s-cookie.json" % (basename, bot.username), "w") as f:
                    jar = bot.browser.get_cookies()
                    json.dump(jar, f, indent=4)
                bot.quit()
            except Exception as ex:
                print(str(ex))

print("Done")