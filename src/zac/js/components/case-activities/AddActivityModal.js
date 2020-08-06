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
        case 'FIELD_CHANGED':
            const { name, value } = action.payload;
            draft[name].value = value;
            return void null;
        case 'RESET':
            return initialState;
        default:
            break;
    }
}


const AddActvityModal = ({ endpoint, isOpen, closeModal }) => {
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
            name: state.name.value,
            remarks: state.remarks.value,
        });
        if (ok) {
            dispatch({
                type: 'RESET',
                payload: null,
            });
            closeModal();
            // TODO: trigger reload of data for list
        } else {

        }
        console.log(data);
        debugger;
    };

    return (
        <Modal
          isOpen={isOpen}
          className="modal"
          onRequestClose={ closeModal }
        >
            <button onClick={ closeModal } className="modal__close btn">&times;</button>

            <h1 className="page-title">Activiteit toevoegen</h1>

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

        </Modal>
    );
};

AddActvityModal.propTypes = {
    endpoint: PropTypes.string.isRequired,
    isOpen: PropTypes.bool.isRequired,
    closeModal: PropTypes.func.isRequired,
};


export { AddActvityModal };
