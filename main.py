import kaptan
from sh import tmux, cut, ErrorReturnCode_1
from pprint import pprint


class SessionExists(Exception):
    pass

class Session(object):

    def __init__(self, **kwargs):
        if 'session_name' not in kwargs:
            raise ValueError('Session requires session_name')
        else:
            for (k, v) in kwargs.items():
                setattr(self, k, v)

    @classmethod
    def new_session(cls, session_name=None, kill_session=False):
        """equivalent to ``tmux new-session``
            returns Session object
        """

        try:
            if len(tmux('has-session', '-t', TEST_SESSION_NAME)) == 0:
                if kill_session:
                    tmux('kill-session', '-t', TEST_SESSION_NAME)
                    pprint('session %s exists. killed it.' % TEST_SESSION_NAME)
                else:
                    raise SessionExists('Session named %s exists' % session_name)
        except ErrorReturnCode_1:
            pass

        pprint('creating session')

        formats = SESSION_FORMATS
        tmux_formats = ['#{%s}' % format for format in formats]

        session_info = tmux(
            'new-session',
            '-d',
            '-s', TEST_SESSION_NAME,
            '-P', '-F%s' % '\t'.join(tmux_formats),   # output
            )

        # combine format keys with values returned from ``tmux list-windows``
        session_info = dict(zip(formats, session_info.split('\t')))

        # clear up empty dict
        session_info = dict((k, v) for k, v in session_info.iteritems() if v)

        session = cls(session_name=session_name)
        session._TMUX = dict()
        for (k, v) in session_info.items():
            session._TMUX[k] = v

        return session

    @classmethod
    def from_tmux(cls, **kwargs):
        if 'session_name' not in kwargs:
            raise ValueError('Session requires session_name')

        session = cls(session_name=kwargs['session_name'])
        session._TMUX = dict()
        for (k, v) in kwargs.items():
            session._TMUX[k] = v

        """
            ``tmux list-windows`` outputs 1 session per line ``\n``.

            -F (FORMATS) allows returning custom sessings, we delimit with
            a tab ``\t``.

            we then use dict+zip to align the format variable with the
            output.

            the ``Window`` object accepts the returned properties  and
            ``Session`` (``self``) object.
        """

        formats = WINDOW_FORMATS
        tmux_formats = ['#{%s}' % format for format in formats]

        windows = tmux(
            'list-windows',                     # ``tmux list-windows``
            '-t%s' % kwargs['session_name'],    # target (session name)
            '-F%s' % '\t'.join(tmux_formats),   # output
            _iter=True                          # iterate line by line
        )

        # combine format keys with values returned from ``tmux list-windows``
        windows = [dict(zip(formats, window.split('\t'))) for window in windows]

        # clear up empty dict
        windows = [
            dict((k, v) for k, v in window.iteritems() if v) for window in windows
        ]

        session._windows = [Window.from_tmux(session=session, **window) for window in windows]

        pprint('%s, windows for %s' % (
            len(session._windows),
            kwargs['session_name']
        ))
        pprint(session._windows)

        return session

    @property
    def windows(self):
        return self._windows

    def __repr__(self):
        # todo test without session_name
        return "%s(%s)" % (self.__class__.__name__, self.session_name)


class Window(object):
    """
        todo
            - @has_session property, or throw an Error
            - Pane
            - __cmd__
    """

    """
     Each window displayed by tmux may be split into one or more panes; each pane takes up a certain area of the
     display and is a separate terminal.  A window may be split into panes using the split-window command.  Windows
     may be split horizontally (with the -h flag) or vertically.  Panes may be resized with the resize-pane command
     (bound to 'C-up', 'C-down' 'C-left' and 'C-right' by default), the current pane may be changed with the
     select-pane command and the rotate-window and swap-pane commands may be used to swap panes without changing
     their position.  Panes are numbered beginning from zero in the order they are created.

     A number of preset layouts are available.  These may be selected with the select-layout command or cycled with
     next-layout (bound to 'Space' by default); once a layout is chosen, panes within it may be moved and resized as
     normal.

     The following layouts are supported:

     even-horizontal
             Panes are spread out evenly from left to right across the window.

     even-vertical
             Panes are spread evenly from top to bottom.

     main-horizontal
             A large (main) pane is shown at the top of the window and the remaining panes are spread from left to
             right in the leftover space at the bottom.  Use the main-pane-height window option to specify the
             height of the top pane.

     main-vertical
             Similar to main-horizontal but the large pane is placed on the left and the others spread from top to
             bottom along the right.  See the main-pane-width window option.

     tiled   Panes are spread out as evenly as possible over the window in both rows and columns.

     In addition, select-layout may be used to apply a previously used layout - the list-windows command displays
     the layout of each window in a form suitable for use with select-layout.  For example:

           $ tmux list-windows
           0: ksh [159x48]
               layout: bb62,159x48,0,0{79x48,0,0,79x48,80,0}
           $ tmux select-layout bb62,159x48,0,0{79x48,0,0,79x48,80,0}



    """
    def __init__(self, **kwargs):

        if 'session' in kwargs:
            self._panes = None
            if isinstance(kwargs['session'], Session):
                self._session = kwargs['session']
            else:
                raise TypeError('session must be a Session object')

        [setattr(self, k, v) for (k, v) in kwargs.items() if k is not 'session']

    def __repr__(self):
        # todo test without session_name
        return "%s(%s %s, %s)" % (
            self.__class__.__name__,
            self._TMUX['window_index'],
            self._TMUX['window_name'],
            self._session
        )

    __LAYOUTS__ = [
        'even-horizontal',  # Panes are spread out evenly from left to right across the window.
        'even-vertical',  # Panes are spread evenly from top to bottom.
        'main-horizontal',
        'main-vertical',
        'tiled'
    ]

    @classmethod
    def from_tmux(cls, session=None, **kwargs):
        """
            ``tmux list-panes`` outputs 1 session per line ``\n``.

            -F (FORMATS) picks settings return, we delimit with tab ``\t``.

            we then use dict+zip to align the format variable with the
            output.

            the ``Pane`` object accepts the returned properties, ``Session``
            object and ``Window`` (``self``) object.
        """

        if not session:
            raise ValueError('``session`` requires valid ``Session`` object')

        window = cls(session=session)

        window._TMUX = dict()
        for (k, v) in kwargs.items():
            window._TMUX[k] = v

        formats = PANE_FORMATS + WINDOW_FORMATS
        tmux_formats = ['#{%s}\t' % format for format in formats]

        panes = tmux(
            'list-panes',
            '-s',                               # for sessions
            '-t%s' % session.session_name,      # target (name of session)
            '-F%s' % ''.join(tmux_formats),     # output
            _iter=True                          # iterate line by line
        )

        # zip and map the results into the dict of formats used above
        panes = [dict(zip(formats, pane.split('\t'))) for pane in panes]

        # clear up empty dict
        panes = [
            dict((k, v) for k, v in pane.iteritems() if v) for pane in panes
        ]

        # filter by window_index
        panes = [
            pane for pane in panes if pane['window_index'] == window._TMUX['window_index']
        ]

        #pprint(panes)

        window._panes = [Pane.from_tmux(session=session, window=window, **pane) for pane in panes]

        pprint('%s, panes for %s' % (
            len(window._panes),
            kwargs['window_index']
        ))
        pprint(window._panes)

        return window

    @property
    def panes(self):
        return self._panes


class Pane(object):

    @classmethod
    def split_window(cls, session=None, window=None, **kwargs):
        """ return a Pane object from ``tmux split-window``
            arguments are results passed from tmux
        """
        pass

    @classmethod
    def from_tmux(cls, session=None, window=None, **kwargs):
        """ return a Pane object
            for freezing current sessions from tmux
        """
        if not session:
            raise ValueError('Pane generated using ``.from_tmux`` must have \
                             ``Session`` object')
        else:
            if not isinstance(session, Session):
                raise TypeError('session must be a Session object')

        if not window:
            raise ValueError('Pane generated using ``.from_tmux`` must have \
                             ``Window`` object')
        else:
            if not isinstance(window, Window):
                raise TypeError('window must be a Window object')

        pane = cls()

        # keep tmux variables into _TMUX
        pane._TMUX = dict()
        for (k, v) in kwargs.items():
            pane._TMUX[k] = v

        pane._session = session
        pane._window = window

        return pane

    def __init__(self, **kwargs):
        pass

    def __repr__(self):
        # todo test without session_name
        return "%s(%s)" % (self.__class__.__name__, self._window)


def get_sessions():
    formats = SESSION_FORMATS
    tmux_formats = ['#{%s}' % format for format in formats]

    sessions = tmux(
        'list-sessions',                    # ``tmux list-windows``
        '-F%s' % '\t'.join(tmux_formats),   # output
        _iter=True                          # iterate line by line
    )

    # combine format keys with values returned from ``tmux list-windows``
    sessions = [dict(zip(formats, session.split('\t'))) for session in sessions]

    # clear up empty dict
    sessions = [
        dict((k, v) for k, v in session.iteritems() if v) for session in sessions
    ]

    sessions = [Session.from_tmux(**session) for session in sessions]

    for session in sessions:
        yield session


"""
    experiment, ALL_FORMATS parsing for session, window, pane object and
    remove blank values

    http://sourceforge.net/p/tmux/tmux-code/ci/master/tree/format.c
"""

SESSION_FORMATS = [
    'session_name',
    'session_windows',
    'session_width',
    'session_height',
    'session_id',
    'session_created',
    'session_created_string',
    'session_attached',
    'session_grouped',
    'session_group',
]

CLIENT_FORMATS = [
    'client_cwd',
    'client_height',
    'client_width',
    'client_tty',
    'client_termname',
    'client_created',
    'client_created_string',
    'client_activity',
    'client_activity_string',
    'client_prefix',
    'client_utf8',
    'client_readonly',
    'client_session',
    'client_last_session',
]

WINDOW_FORMATS = [
    # format_window()
    'window_id',
    'window_name',
    'window_width',
    'window_height',
    'window_layout',
    'window_panes',
    # format_winlink()
    'window_index',
    'window_flags',
    'window_active',
    'window_bell_flag',
    'window_activity_flag',
    'window_silence_flag',
]

PANE_FORMATS = [
    'history_size',
    'history_limit',
    'history_bytes',
    'pane_index',
    'pane_width',
    'pane_height',
    'pane_title',
    'pane_id',
    'pane_active',
    'pane_dead',
    'pane_in_mode',
    'pane_synchronized',
    'pane_tty',
    'pane_pid',
    'pane_start_command',
    'pane_start_path',
    'pane_current_path',
    'pane_current_command',

    'cursor_x',
    'cursor_y',
    'scroll_region_upper',
    'scroll_region_lower',
    'saved_cursor_x',
    'saved_cursor_y',

    'alternate_on',
    'alternate_saved_x',
    'alternate_saved_y',

    'cursor_flag',
    'insert_flag',
    'keypad_cursor_flag',
    'keypad_flag',
    'wrap_flag',

    'mouse_standard_flag',
    'mouse_button_flag',
    'mouse_any_flag',
    'mouse_utf8_flag',
]


config = kaptan.Kaptan(handler="yaml")
config.import_config("""
    windows:
        - editor:
            layout: main-vertical
            panes:
                - vim
                - cowsay "hey"
        - server: htop
        - logs: tail -f logs/development.log
    """)

""" expand inline config
    dict({'session_name': { dict })

    to

    dict({ name='session_name', **dict})
"""
windows = list()
for window in config.get('windows'):

    if len(window) == int(1):
        name = window.iterkeys().next()  # get window name

        """expand
            window[name] = 'command'

            to

            window[name] = {
                panes=['command']
            }
        """
        if isinstance(window[name], basestring):
            windowoptions = dict(
                panes=[window[name]]
            )
        else:
            windowoptions = window[name]

        window = dict(name=name, **windowoptions)
        if len(window['panes']) > int(1):
            pass

    windows.append(window)


for session in get_sessions():
    for window in session.windows:
        for pane in window.panes:
            pass

tmux('switch-client', '-t0')
tmux('switch-client', '-ttony')

TEST_SESSION_NAME = 'tmuxwrapper_dev'

session = Session.new_session(
    session_name=TEST_SESSION_NAME,
    kill_session=True
)
#tmux('new-session', '-d', '-s', TEST_SESSION_NAME)
tmux('switch-client', '-t', TEST_SESSION_NAME)

tmux('split-window', '-h', '-p30')
#tmux('send-keys', '-t', 'cd /srv/www/flaskr')
tmux('split-window', '-v', '-p50')
tmux('split-window', '-v', '-p50')
tmux('display-panes')
