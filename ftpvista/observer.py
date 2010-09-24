# -*- coding: utf-8 -*-

"""Observer pattern implementation.

Simple implementation of the Observer pattern.
Provides a publish/subscribe mechanism.

"""

class Observer (object):
    """
        Observer interface.
    """

    def update(self, observable, arg):
        """
            Method called whenever the observed object's state changed.
            Must be overriden.

            observable : the observee object sending the notification
            arg : optional argument passed by the observee
        """
        raise NotImplementedError


class Observable (object):
    """
        Observable base class.

        Must be inherited by the class willing to be observed.
    """

    def __init__(self):
        self._observers = set()

    def add_observer(self, observer):
        self._observers.add(observer)

    def delete_observer(self, observer):
        self._observers.remove(observer)

    def delete_observers(self):
        self._observers.clear()

    def count_observers(self):
        return len(self._observers)

    def notify_observers(self, arg=None):
        """
            Notifies every observer that the state of this object has changed.
            arg is an optionnal parameter to pass to the observers.
        """
        for o in self._observers:
            o.update(self, arg)
