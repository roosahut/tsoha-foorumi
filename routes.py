import string
from app import app
from flask import render_template, request, redirect
import users
import forums as fr
import chains as ch
import messages as ms


@app.route('/')
def index():
    forums = fr.get_forums_info()
    users_list = users.get_all_users()
    return render_template('index.html', forums=forums, users=users_list)


@app.route('/register', methods=['get', 'post'])
def reqister():
    if request.method == 'GET':
        return render_template('register.html')

    if request.method == 'POST':
        username = request.form['username']
        if len(username) > 20:
            return render_template('error.html', message='The username is too long, it should be 4-20 characters long')
        if len(username) < 4:
            return render_template('error.html', message='Username is too short, it should be 4-20 characters long')
        characters = string.ascii_letters + string.digits + 'äåöÄÅÖ'
        for i in username:
            if i not in characters:
                return render_template('error.html', message='Username must have only letters and numbers in it')

        password1 = request.form['password1']
        password2 = request.form['password2']
        if password1 != password2:
            return render_template('error.html', message='The passwords are not the same')
        if len(password1) < 8:
            return render_template('error.html', message='Password is too short')

        role = request.form['role']
        if role not in ['1', '2']:
            return render_template('error.html', message='Unknown user')

        if not users.register(username, password1, role):
            return render_template('error.html', message='The registration was unsuccesful, try a different username')

        return redirect('/')


@app.route('/login', methods=['get', 'post'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not users.login(username, password):
            return render_template('error.html', message='Wrong username or password')
        return redirect('/')


@app.post('/logout')
def logout():
    users.logout()
    return redirect('/')


@app.route('/forum/<int:forum_id>')
def show_forum(forum_id):
    if fr.is_forum_deleted(forum_id):
        return render_template('error.html', message='This forum is deleted')

    if fr.has_user_forum_access(forum_id, users.user_id()):
        chains = ch.get_chains_info_in_forum(forum_id)
        name = fr.get_forum_name(forum_id)[0]
        return render_template('forum.html', id=forum_id, chains=chains, name=name)
    else:
        return render_template("error.html", message="No access to this forum")


@app.route('/forum/<int:forum_id>/<int:chain_id>')
def show_chain(forum_id, chain_id):
    if ch.is_chain_deleted(chain_id):
        return render_template('error.html', message='This chain is deleted')

    if fr.has_user_forum_access(forum_id, users.user_id()):
        messages = ms.get_messages_info(chain_id)
        chain_info = ch.get_chains_info(chain_id)[0]
        return render_template('chain.html', id=chain_id, forum_id=forum_id, messages=messages, chain_info=chain_info)

    else:
        return render_template("error.html", message="No access to this forum")


@app.route('/forum/<int:forum_id>/new_chain', methods=['get', 'post'])
def add_new_chain(forum_id):
    if request.method == 'GET':
        if fr.is_forum_deleted(forum_id):
            return render_template('error.html', message='This forum is deleted')

        if fr.has_user_forum_access(forum_id, users.user_id()) and users.user_id() > 0:
            return render_template('new_chain.html', forum_id=forum_id)

        else:
            return render_template("error.html", message="No access")

    if request.method == 'POST':
        users.check_csrf()

        if fr.is_forum_deleted(forum_id):
            return render_template('error.html', message='This forum is deleted')

        if fr.has_user_forum_access(forum_id, users.user_id()) and users.user_id() > 0:
            headline = request.form['headline']
            if headline == "":
                return render_template("error.html", message="You have to write a headline")
            if 2 > len(headline) > 20:
                return render_template("error.html", message="Headline must be between 2-20 characters")

            message = request.form['message']
            if message == "":
                return render_template("error.html", message="You have to write a message to start the chain")
            if len(message) > 10000:
                return render_template("error.html", message="The message is too long")

            chain_id = ch.add_new_chain(
                headline, message, users.user_id(), forum_id)

            return redirect(f'/forum/{forum_id}/{chain_id}')

        else:
            return render_template("error.html", message="No access")


@app.post('/new_message')
def new_message():
    users.check_csrf()

    chain_id = request.form['chain_id']
    forum_id = request.form['forum_id']

    if ch.is_chain_deleted(chain_id):
        return render_template('error.html', message='This chain is deleted')

    if fr.has_user_forum_access(forum_id, users.user_id()) and users.user_id() > 0:

        message = request.form['message']
        if message == "":
            return render_template("error.html", message="You have to write a message to submit")
        if len(message) > 10000:
            return render_template("error.html", message="The message is too long")

        ms.add_new_message(message, users.user_id(), chain_id)

        return redirect(f'/forum/{forum_id}/{chain_id}')

    else:
        return render_template("error.html", message="No access")


@app.post('/new_forum')
def new_forum():
    users.check_csrf()
    users.require_role(2)

    name = request.form['name']
    if name == "":
        return render_template("error.html", message="You have to give the forum a name")
    if 2 > len(name) > 20:
        return render_template("error.html", message="The forum name must be 2-10 characters")

    creator_id = users.user_id()

    access_choice = request.form['access_choice']
    if access_choice not in ['public', 'private']:
        return render_template("error.html", message="Unknown access choice")

    if access_choice == 'public':
        forum_id = fr.add_new_forum(name, creator_id, False)

    elif access_choice == 'private':
        forum_id = fr.add_new_forum(name, creator_id, True)

        allowed_users = request.form.getlist('allowed_user')
        for user_id in allowed_users:
            fr.add_access_to_secret_forum(forum_id, user_id)

    return redirect(f'/')


@app.post('/delete_message')
def delete_message():
    users.check_csrf()

    forum_id = request.form['forum_id']
    message_id = request.form['message_id']

    if ms.is_message_deleted(message_id):
        return render_template('error.html', message='This message is already deleted')

    if fr.has_user_forum_access(forum_id, users.user_id()) and ms.is_user_message_writer(message_id, users.user_id()):
        ms.delete_message(message_id, users.user_id())

        chain_id = request.form['chain_id']
        return redirect(f'/forum/{forum_id}/{chain_id}')

    else:
        return render_template("error.html", message="No access")


@app.route('/forum/<int:forum_id>/<int:chain_id>/<int:message_id>', methods=['get', 'post'])
def edit_message(forum_id, chain_id, message_id):
    if request.method == 'GET':
        if ms.is_message_deleted(message_id):
            return render_template('error.html', message='This message is deleted')

        if fr.has_user_forum_access(forum_id, users.user_id()) and ms.is_user_message_writer(message_id, users.user_id()):
            return render_template('edit_message.html', forum_id=forum_id, chain_id=chain_id, message_id=message_id)
        else:
            return render_template("error.html", message="No access")

    if request.method == 'POST':
        users.check_csrf()

        if ms.is_message_deleted(message_id):
            return render_template('error.html', message='This message is deleted')

        if fr.has_user_forum_access(forum_id, users.user_id()) and ms.is_user_message_writer(message_id, users.user_id()):
            message = request.form['message']
            if message == "":
                return render_template("error.html", message="You have to write a message")
            if len(message) > 10000:
                return render_template("error.html", message="The message is too long")
            writer_id = users.user_id()

            ms.edit_message(message_id, message, writer_id)

            return redirect(f'/forum/{forum_id}/{chain_id}')

        else:
            return render_template("error.html", message="No access")


@app.route('/forum/<int:forum_id>/<int:chain_id>/edit_headline', methods=['get', 'post'])
def edit_headline(forum_id, chain_id):
    if request.method == 'GET':
        if ch.is_chain_deleted(chain_id):
            return render_template('error.html', message='This chain is deleted')

        if fr.has_user_forum_access(forum_id, users.user_id()) and ch.is_user_chain_creator(chain_id, users.user_id()):
            return render_template('edit_headline.html', forum_id=forum_id, chain_id=chain_id)

        else:
            return render_template("error.html", message="No access")

    if request.method == 'POST':
        users.check_csrf()

        if ch.is_chain_deleted(chain_id):
            return render_template('error.html', message='This chain is deleted')

        if fr.has_user_forum_access(forum_id, users.user_id()) and ch.is_user_chain_creator(chain_id, users.user_id()):
            headline = request.form['headline']
            if headline == "":
                return render_template("error.html", message="You have to write something to be the headline")
            if 2 > len(headline) > 20:
                return render_template("error.html", message="Headline must be between 2-20 characters")
            writer_id = users.user_id()

            ch.edit_chain_headline(chain_id, headline, writer_id)

            return redirect(f'/forum/{forum_id}/{chain_id}')

        else:
            return render_template("error.html", message="No access")


@app.post('/delete_chain')
def delete_chain():
    users.check_csrf()

    forum_id = request.form['forum_id']
    chain_id = request.form['chain_id']

    if ch.is_chain_deleted(chain_id):
        return render_template('error.html', message='This chain is already deleted')

    if fr.has_user_forum_access(forum_id, users.user_id()) and ch.is_user_chain_creator(chain_id, users.user_id()):
        ch.delete_chain(chain_id, users.user_id())

        return redirect(f'/forum/{forum_id}')

    else:
        return render_template("error.html", message="No access to this forum")


@app.post('/delete_forum')
def delete_forum():
    users.check_csrf()
    users.require_role(2)

    forum_id = request.form['forum_id']

    if fr.is_forum_deleted(forum_id):
        return render_template('error.html', message='This forum is already deleted')

    fr.delete_forum(forum_id)

    forum_id = request.form['forum_id']
    return redirect(f'/')


@app.route('/search', methods=['get', 'post'])
def search_messages():
    if request.method == 'GET':
        is_words = False
        return render_template('search.html', is_words=is_words)

    if request.method == 'POST':
        users.check_csrf()

        word = request.form['word']
        if word == "":
            return render_template("error.html", message="You have to input a word or letter")
        messages = ms.search_messages_with_word(word, users.user_id())
        is_words = True

        return render_template('search.html', messages=messages, is_words=is_words)


@app.post('/like_message')
def like_message():
    users.check_csrf()

    forum_id = request.form['forum_id']
    message_id = request.form['message_id']

    if ms.is_message_deleted(message_id):
        return render_template('error.html', message='This message is deleted')

    if fr.has_user_forum_access(forum_id, users.user_id()) and users.user_id() > 0:
        liker_id = users.user_id()

        if not ms.has_user_liked_message(message_id, liker_id):
            return render_template("error.html", message="You can't like the same message twice")
        else:
            ms.like_message(message_id, liker_id)

            chain_id = request.form['chain_id']
            return redirect(f'/forum/{forum_id}/{chain_id}')

    else:
        return render_template("error.html", message="No access")


@app.post('/unlike_message')
def unlike_message():
    users.check_csrf()

    forum_id = request.form['forum_id']
    message_id = request.form['message_id']

    if ms.is_message_deleted(message_id):
        return render_template('error.html', message='This message is deleted')

    if fr.has_user_forum_access(forum_id, users.user_id()) and users.user_id() > 0:
        liker_id = users.user_id()

        if not ms.has_user_unliked_message(message_id, liker_id):
            return render_template("error.html", message="You can't unlike the same message twice")
        else:
            ms.unlike_message(message_id, liker_id)

            chain_id = request.form['chain_id']
            return redirect(f'/forum/{forum_id}/{chain_id}')

    else:
        return render_template("error.html", message="No access")
