import React from 'react';
import PropTypes from 'prop-types';
import Modal from 'react-modal';

import { TextInput } from '../forms/Inputs';
import { TextArea } from '../forms/TextArea';
import { SubmitRow } from '../forms/Utils';


const AddActvityModal = ({ isOpen, closeModal }) => {
    return (
        <Modal
          isOpen={isOpen}
          className="modal"
          onRequestClose={ closeModal }
        >
            <button onClick={ closeModal } className="modal__close btn">&times;</button>

            <h1 className="page-title">Activiteit toevoegen</h1>

            <form className="form form--modal">
                <TextInput id="id_name" name="name" label="Naam" required={true} />
                <TextArea id="id_remarks" name="remarks" label="Opmerkingen" />
                <SubmitRow text="Toevoegen"/>
            </form>

        </Modal>
    );
};

AddActvityModal.propTypes = {
    isOpen: PropTypes.bool.isRequired,
    closeModal: PropTypes.func.isRequired,
};


export { AddActvityModal };
