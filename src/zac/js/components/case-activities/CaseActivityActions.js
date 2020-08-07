import React from 'react';
import PropTypes from 'prop-types';

import Modal from 'react-modal';
import { useImmerReducer } from "use-immer";

import { SubmitRow } from '../forms/Utils';
import { Activity } from './types';


const ConfirmModal = ({ isOpen, text, onConfirm, closeModal }) => {
    return (
        <Modal
          isOpen={isOpen}
          className="modal"
          onRequestClose={ closeModal }
        >
            <button onClick={ closeModal } className="modal__close btn">&times;</button>
            <strong>{text}</strong>
            <SubmitRow text="Bevestigen" onClick={onConfirm} />
        </Modal>
    );
};


const initialModalState = {
    openModal: null,
};


const modalReducer = (draft, action) => {
    switch (action.type) {
        case 'OPEN_MODAL': {
            draft.openModal = action.payload;
            break;
        }
        case 'CLOSE_MODAL': {
            draft.openModal = null;
            break;
        }
        default:
            console.error(`Unknown action: ${action.type}`);
            break;
    }
};


const CaseActivityActions = ({ activity, closeActivity }) => {
    if (activity.status !== 'on_going') {
        return null;
    }
    const [{ openModal }, dispatch] = useImmerReducer(modalReducer, initialModalState);

    return (
        <div className="btn-group btn-group--slim case-activity__actions">
            <button
                type="button"
                className="btn btn--choice"
                onClick={ () => dispatch({
                    type: 'OPEN_MODAL',
                    payload: 'closeActivity',
                }) }
            > Afsluiten </button>

            <button
                type="button"
                className="btn btn--choice"
                onClick={ () => dispatch({
                    type: 'OPEN_MODAL',
                    payload: 'deleteActivity',
                }) }
            > Verwijderen </button>

            <ConfirmModal
                isOpen={ openModal === 'closeActivity' }
                text="Weet je zeker dat je deze activiteit wil sluiten?"
                onConfirm={ closeActivity }
                closeModal={ () => dispatch({type: 'CLOSE_MODAL'}) }
            />

            <ConfirmModal
                isOpen={ openModal === 'deleteActivity' }
                text="Weet je zeker dat je deze activiteit PERMANENT wil verwijderen?"
                onConfirm={ () => alert('TODO') }
                closeModal={ () => dispatch({type: 'CLOSE_MODAL'}) }
            />

        </div>
    );
};

CaseActivityActions.propTypes = {
    activity: Activity.isRequired,
    closeActivity: PropTypes.func.isRequired,
};


export { CaseActivityActions };
