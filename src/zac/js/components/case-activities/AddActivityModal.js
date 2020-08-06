import React from 'react';
import PropTypes from 'prop-types';
import Modal from 'react-modal';


const AddActvityModal = ({ isOpen, closeModal }) => {
    return (
        <Modal
          isOpen={isOpen}
          className="modal"
          onRequestClose={ closeModal }
        >
            <button onClick={ closeModal } className="modal__close btn">&times;</button>

            Hello world.

        </Modal>
    );
};

AddActvityModal.propTypes = {
    isOpen: PropTypes.bool.isRequired,
    closeModal: PropTypes.func.isRequired,
};


export { AddActvityModal };
