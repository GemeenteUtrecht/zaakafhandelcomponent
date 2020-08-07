import React, { useContext } from 'react';
import PropTypes from 'prop-types';
import Modal from 'react-modal';

import { useImmerReducer } from "use-immer";

import { CsrfTokenContext } from '../forms/context';
import { TextInput } from '../forms/Inputs';
import { TextArea } from '../forms/TextArea';
import { SubmitRow } from '../forms/Utils';
import { post } from '../../utils/fetch';


const initialState = {
    name: {
        value: '',
        errors: [],
    },
    remarks: {
        value: '',
        errors: [],
    },
};

function reducer(draft, action) {
    switch (action.type) {
        case 'RESET':
            return initialState;

        case 'FIELD_CHANGED': {
            const { name, value } = action.payload;
            draft[name].value = value;
            draft[name].errors = [];
            break;
        }

        case 'VALIDATION_ERRORS': {
            const errors = action.payload;
            for (const [field, errors] of Object.entries(errors)) {
                draft[field].errors = errors;
            }
            break;
        }

        default:
            break;
    }
}


const AddActvityForm = ({ zaak, endpoint, onCreated }) => {
    const [state, dispatch] = useImmerReducer(reducer, initialState);
    const csrftoken = useContext(CsrfTokenContext);

    const onFieldChange = (event) => {
        const { name, value } = event.target;
        dispatch({
            type: 'FIELD_CHANGED',
            payload: {
                name,
                value
            }
        });
    };

    /**
     * Submit the form data to the API endpoint
     * @param  {DOMEvent} event The Submit event
     * @return {Void}
     */
    const onSubmit = async (event) => {
        event.preventDefault();
        const {ok, status, data} = await post(endpoint, csrftoken, {
            zaak: zaak,
            name: state.name.value,
            remarks: state.remarks.value,
        });
        if (ok) {
            dispatch({
                type: 'RESET',
                payload: null,
            });
            onCreated(data);
        } else {
            dispatch({
                type: 'VALIDATION_ERRORS',
                payload: data,
            });
        }
    };

    return (
        <form className="form form--modal" onSubmit={onSubmit}>
            <TextInput
                id="id_name"
                name="name"
                label="Naam"
                required={true}
                onChange={ onFieldChange }
                value={state.name.value}
                errors={state.name.errors}
            />
            <TextArea
                id="id_remarks"
                name="remarks"
                label="Opmerkingen"
                onChange={ onFieldChange }
                value={state.remarks.value}
                errors={state.remarks.errors}
            />
            <SubmitRow text="Toevoegen"/>
        </form>
    );
};

AddActvityForm.propTypes = {
    zaak: PropTypes.string.isRequired,
    endpoint: PropTypes.string.isRequired,
    onCreated: PropTypes.func.isRequired,
};


const AddActvityModal = ({ zaak, endpoint, isOpen, closeModal, refresh }) => {
    const [state, dispatch] = useImmerReducer(reducer, initialState);
    const csrftoken = useContext(CsrfTokenContext);

    const onCreated = (data) => {
        refresh();
        closeModal();
    };

    return (
        <Modal
          isOpen={isOpen}
          className="modal"
          onRequestClose={ closeModal }
        >
            <button onClick={ closeModal } className="modal__close btn">&times;</button>
            <h1 className="page-title">Activiteit toevoegen</h1>
            <AddActvityForm zaak={zaak} endpoint={endpoint} onCreated={onCreated} />
        </Modal>
    );
};

AddActvityModal.propTypes = {
    zaak: PropTypes.string.isRequired,
    endpoint: PropTypes.string.isRequired,
    isOpen: PropTypes.bool.isRequired,
    closeModal: PropTypes.func.isRequired,
    refresh: PropTypes.func.isRequired,
};


export { AddActvityModal };
