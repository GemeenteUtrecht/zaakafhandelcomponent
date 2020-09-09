import React, { useState } from 'react';
import PropTypes from 'prop-types';
import Modal from "react-modal";

import { AddDocument } from '../../components/documents/AddDocument';


const AddZaakDocument = ({ zaakUrl, onUploadComplete }) => {
    const [modalOpen, setModalOpen] = useState(false);
    const closeModal = () => setModalOpen(false);

    return (
        <React.Fragment>
            <div className="btn-row">
                <a
                    href="#"
                    role="button"
                    className="btn btn--small"
                    onClick={ (e) => {
                        e.preventDefault();
                        setModalOpen(true);
                    } }
                >
                <i className="material-icons">add</i>
                Document toevoegen
                </a>
            </div>

            <Modal
              isOpen={ modalOpen }
              className="modal"
              onRequestClose={ closeModal }
            >
                <button onClick={ closeModal } className="modal__close btn">&times;</button>
                <h1 className="page-title">Document toevoegen</h1>
                <AddDocument
                    zaakUrl={ zaakUrl }
                    onUploadComplete={ onUploadComplete }
                    inModal
                />
            </Modal>

        </React.Fragment>
    );
};

AddZaakDocument.propTypes = {
    zaakUrl: PropTypes.string.isRequired,
    onUploadComplete: PropTypes.func.isRequired,
};


export { AddZaakDocument };
