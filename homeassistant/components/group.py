"""
homeassistant.components.groups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Provides functionality to group devices that can be turned on or off.
"""

import logging

import homeassistant as ha

DOMAIN = "group"

ENTITY_ID_FORMAT = DOMAIN + ".{}"

STATE_ATTR_ENTITY_IDS = "entity_ids"

_GROUP_TYPES = {
    "on_off": (ha.STATE_ON, ha.STATE_OFF),
    "home_not_home": (ha.STATE_HOME, ha.STATE_NOT_HOME)
}


def _get_group_type(state):
    """ Determine the group type based on the given group type. """
    for group_type, states in _GROUP_TYPES.items():
        if state in states:
            return group_type

    return None


def is_on(statemachine, group):
    """ Returns if the group state is in its ON-state. """
    state = statemachine.get_state(group)

    if state:
        group_type = _get_group_type(state.state)

        if group_type:
            # We found group_type, compare to ON-state
            return state.state == _GROUP_TYPES[group_type][0]
        else:
            return False
    else:
        return False


def get_entity_ids(statemachine, group):
    """ Get the entity ids that make up this group. """
    try:
        return statemachine.get_state(group).attributes[STATE_ATTR_ENTITY_IDS]
    except (AttributeError, KeyError):
        # AttributeError if state did not exist
        # KeyError if key did not exist in attributes
        return []


# pylint: disable=too-many-branches
def setup(bus, statemachine, name, entity_ids):
    """ Sets up a group state that is the combined state of
        several states. Supports ON/OFF and DEVICE_HOME/DEVICE_NOT_HOME. """

    logger = logging.getLogger(__name__)

    # Loop over the given entities to:
    #  - determine which group type this is (on_off, device_home)
    #  - if all states exist and have valid states
    #  - retrieve the current state of the group
    errors = []
    group_type, group_on, group_off, group_state = None, None, None, None

    for entity_id in entity_ids:
        state = statemachine.get_state(entity_id)

        # Try to determine group type if we didn't yet
        if not group_type and state:
            group_type = _get_group_type(state.state)

            if group_type:
                group_on, group_off = _GROUP_TYPES[group_type]
                group_state = group_off

            else:
                # We did not find a matching group_type
                errors.append("Found unexpected state '{}'".format(
                              name, state.state))

                break

        # Check if entity exists
        if not state:
            errors.append("Entity {} does not exist".format(entity_id))

        # Check if entity is valid state
        elif state.state != group_off and state.state != group_on:

            errors.append("State of {} is {} (expected: {}, {})".format(
                entity_id, state.state, group_off, group_on))

        # Keep track of the group state to init later on
        elif group_state == group_off and state.state == group_on:
            group_state = group_on

    if errors:
        logger.error("Error setting up state group {}: {}".format(
            name, ", ".join(errors)))

        return False

    group_entity_id = ENTITY_ID_FORMAT.format(name)
    state_attr = {STATE_ATTR_ENTITY_IDS: entity_ids}

    # pylint: disable=unused-argument
    def _update_group_state(entity_id, old_state, new_state):
        """ Updates the group state based on a state change by a tracked
            entity. """

        cur_group_state = statemachine.get_state(group_entity_id).state

        # if cur_group_state = OFF and new_state = ON: set ON
        # if cur_group_state = ON and new_state = OFF: research
        # else: ignore

        if cur_group_state == group_off and new_state.state == group_on:

            statemachine.set_state(group_entity_id, group_on, state_attr)

        elif cur_group_state == group_on and new_state.state == group_off:

            # Check if any of the other states is still on
            if not any([statemachine.is_state(ent_id, group_on)
                        for ent_id in entity_ids if entity_id != ent_id]):
                statemachine.set_state(group_entity_id, group_off, state_attr)

    for entity_id in entity_ids:
        ha.track_state_change(bus, entity_id, _update_group_state)

    statemachine.set_state(group_entity_id, group_state, state_attr)

    return True