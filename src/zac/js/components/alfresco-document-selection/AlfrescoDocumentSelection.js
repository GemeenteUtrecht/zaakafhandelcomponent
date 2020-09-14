import React, { useState } from 'react';
import PropTypes from 'prop-types';
import Modal from 'react-modal';

import { AlfrescoBrowser } from './AlfrescoBrowser';


const AlfrescoDocumentSelection = ({ username, password, name, zaaktype, bronorganisatie, id }) => {
    const [isOpen, setIsOpen] = useState(false);
    const closeModal = () => setIsOpen(false);

    return (
        <div>
            <button type="button" onClick={ () => setIsOpen(true) } className="btn btn--small">
                <i className="material-icons">search</i>
                Zoek in Alfresco
            </button>

            {/*
            <input
                type="text"
                name={name}
                id={id}
                defaultValue=""
                placeholder="Document API url"
            />
            */}

            <Modal
              isOpen={isOpen}
              className="modal modal--large"
              onRequestClose={ closeModal }
              ariaHideApp={false}
            >
                <button onClick={ closeModal } className="modal__close btn">&times;</button>
                <AlfrescoBrowser
                    username={username}
                    password={password}
                    zaaktype={zaaktype}
                    bronorganisatie={bronorganisatie}
                />
            </Modal>
        </div>
    );
};

AlfrescoDocumentSelection.propTypes = {
    username: PropTypes.string.isRequired,  // username of the Alfresco API # TODO - use different auth
    password: PropTypes.string.isRequired,  // username of the Alfresco API # TODO - use different auth
    name: PropTypes.string.isRequired,  // HTML name of the input
    zaaktype: PropTypes.string.isRequired,  // URL of the zaaktype
    bronorganisatie: PropTypes.string.isRequired,  // RSIN of the bronorganisatie to use for EIO in the API
    id: PropTypes.string,  // HTML id of the input
};


export { AlfrescoDocumentSelection };
