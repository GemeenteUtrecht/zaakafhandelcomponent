import React, { useState } from 'react';
import PropTypes from 'prop-types';
import Modal from 'react-modal';

import { AlfrescoBrowser } from './AlfrescoBrowser';


const AlfrescoDocumentSelection = ({ name, zaaktype, bronorganisatie, id }) => {
    const [isOpen, setIsOpen] = useState(false);
    const closeModal = () => setIsOpen(false);

    const [documentUrl, setDocumentUrl] = useState('');

    const onEIOCreated = (url) => {
        setDocumentUrl(url);
        closeModal();
    };

    return (
        <div>
            <input
                type="hidden"
                name={name}
                id={id}
                defaultValue={documentUrl}
                placeholder="Document API url"
            />

            <button type="button" onClick={ () => setIsOpen(true) } className="btn btn--small">
                <i className="material-icons">search</i>
                { documentUrl ? "Wijzig" : "Zoek in Alfresco" }
            </button>

            <Modal
              isOpen={isOpen}
              className="modal modal--large"
              onRequestClose={ closeModal }
              ariaHideApp={false}
            >
                <button onClick={ closeModal } className="modal__close btn">&times;</button>
                <AlfrescoBrowser
                    zaaktype={zaaktype}
                    bronorganisatie={bronorganisatie}
                    onEIOCreated={onEIOCreated}
                />
            </Modal>
        </div>
    );
};

AlfrescoDocumentSelection.propTypes = {
    name: PropTypes.string.isRequired,  // HTML name of the input
    zaaktype: PropTypes.string.isRequired,  // URL of the zaaktype
    bronorganisatie: PropTypes.string.isRequired,  // RSIN of the bronorganisatie to use for EIO in the API
    id: PropTypes.string,  // HTML id of the input
};


export { AlfrescoDocumentSelection };
