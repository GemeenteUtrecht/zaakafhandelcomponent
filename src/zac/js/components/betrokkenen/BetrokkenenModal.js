import React, { useState } from 'react';
import Modal from 'react-modal';
import PropTypes from 'prop-types';
import BetrokkenenForm from './BetrokkenenForm';
import BetrokkenenResult from './BetrokkenenResult';

const modalStyles = {
    overlay: {
        zIndex: '100',
        overflowY: 'scroll',
    },
};

const ModalChild = ({ bsn }) => {
    const [showFormState, setShowForm] = useState(true);
    const [resultData, setResultData] = useState({});

    function handleFormOutput(data) {
        setResultData(data);
        setShowForm(false);
    }

    if (!showFormState) {
        return <BetrokkenenResult data={resultData} />;
    }
    return (
        <BetrokkenenForm
            bsn={bsn}
            onFetchBetrokkeneComplete={(data) => { handleFormOutput(data); }}
        />
    );
};

ModalChild.propTypes = {
    bsn: PropTypes.string,
};

const BetrokkenenModal = ({ isOpen, setIsOpen, bsn }) => {
    const closeModal = () => setIsOpen(false);

    return (
        <Modal
            isOpen={isOpen}
            onRequestClose={closeModal}
            className="modal"
            style={modalStyles}
        >
            <button type="button" onClick={closeModal} className="modal__close btn">&times;</button>
            <ModalChild bsn={bsn} />
        </Modal>
    );
};

BetrokkenenModal.propTypes = {
    isOpen: PropTypes.bool.isRequired,
    setIsOpen: PropTypes.func.isRequired,
    bsn: PropTypes.string.isRequired,
};

export default BetrokkenenModal;
