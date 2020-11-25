import React, { useState, useContext } from 'react';
import PropTypes from 'prop-types';

import { useImmerReducer } from "use-immer";

import { CsrfTokenContext } from '../forms/context';
import { SubmitRow } from '../forms/Utils';
import { post } from '../../utils/fetch';
import { EventsContext } from './context';

const initialState = {
    value: '',
    errors: [],
    active: false,
};


const reducer = (draft, action) => {
    switch (action.type) {
        case 'RESET':
            return initialState;

        case 'NOTES_CHANGED': {
            draft.value = action.payload;
            if (!draft.value) {
                draft.active = false;
            }
            break;
        }

        case 'FOCUS': {
            draft.active = action.payload;
            break;
        }

        case 'BLUR': {
            if (!draft.value) {
                draft.active = false;
            }
            break;
        }

        default:
            break;
    }
};


const AddNotes = ({ activityId }) => {
    const eventsContext = useContext(EventsContext);
    const csrftoken = useContext(CsrfTokenContext);

    const [
        { value, active },
        dispatch
    ] = useImmerReducer(reducer, initialState);

    const createEvent = async (event) => {
        event.preventDefault();
        const {ok, status, data} = await post(eventsContext.endpoint, csrftoken, {
            activity: activityId,
            notes: value,
        });

        if (!ok) {
            console.error(data);
        } else {
            dispatch({
                type: "RESET",
                payload: null
            });
            eventsContext.onCreate(data);
        }
    };

    const expanded = active || value;
    const className = `case-activity__add-note ${ expanded ? 'case-activity__add-note--active' : '' }`;

    return (
        <form className="case-activity__note-form" onSubmit={createEvent}>
            <textarea
                name="notes"
                className={className}
                value={active ? value : value.split('\n')[0]}
                onChange={ (event) => dispatch({
                    type: 'NOTES_CHANGED',
                    payload: event.target.value,
                }) }
                placeholder="Notitie toevoegen"
                required={true}
                onFocus={ () => dispatch({type: 'FOCUS', payload: true}) }
                onBlur={ () => dispatch({type: 'BLUR', payload: true}) }
            />
            {
                expanded ?
                <SubmitRow
                    text="toevoegen"
                    btnModifier="small"
                />
                : null
            }
        </form>
    );
};

AddNotes.propTypes = {
    activityId: PropTypes.number.isRequired,
};


export { AddNotes };
