import React, { useState } from 'react';
import PropTypes from 'prop-types';

import Modal from 'react-modal';
import AsyncSelect from 'react-select/async';

import { get } from '../../utils/fetch';
import { getAuthorName as getUserName } from '../../views/zaak-detail/utils';
import { SubmitRow } from '../../components/forms/Utils';


const ENDPOINT = '/accounts/api/users';  // TODO: use context provider for this?

const getUsers = async (inputValue) => {
    const response = await get(ENDPOINT, {search: inputValue});
    const results = response.results;
    return results.map( (user) => {
        return {
            value: user.id,
            label: getUserName(user),
            userObject: user,
        };
    } );
};


const UserSelection = ({ onSelection, btnLabel='Selecteer gebruiker' }) => {
    const [modalOpen, setModalOpen] = useState(false);
    const [selectedUser, setSelectedUser] = useState(null);

    const closeModal = () => setModalOpen(false);

    const onSubmit = (event) => {
        event.preventDefault();
        onSelection(selectedUser);
    };

    return (
        <React.Fragment>

            <button type="button" className="btn btn--small" onClick={ () => setModalOpen(true) }>
                {btnLabel}
            </button>

            <Modal
              isOpen={modalOpen}
              className="modal"
              onRequestClose={ closeModal }
            >
                <button onClick={ closeModal } className="modal__close btn">&times;</button>
                <h1 className="page-title">Medewerker zoeken</h1>

                <form onSubmit={onSubmit}>
                    <AsyncSelect
                        autoFocus
                        isClearable
                        cacheOptions
                        defaultOptions={false}
                        loadOptions={ getUsers }
                        onChange={ (value) => setSelectedUser(value ? value.userObject : null) }
                    />

                    <div className="modal__submitrow">
                        <SubmitRow text="Selecteer" />
                    </div>
                </form>

            </Modal>
        </React.Fragment>
    );
};

UserSelection.propTypes = {
    onSelection: PropTypes.func.isRequired,
    btnLabel: PropTypes.string,
};


export { UserSelection };
