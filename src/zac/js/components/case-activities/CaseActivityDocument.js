import React, { useState } from 'react';
import PropTypes from 'prop-types';

import Modal from 'react-modal';

import { patch } from '../../utils/fetch';
import { CsrfTokenContext } from '../forms/context';
import { IconedText } from '../IconedText';
import { AddDocument } from '../documents/AddDocument';
import { Activity } from './types';


const CaseActivityDocument = ({ activity, canMutate=false }) => {
    // TODO: flesh out more
    if (activity.document) {
        return (
            <a className="btn btn--small" onClick={() => alert('todo')}>
                Toon documentinformatie
            </a>
        );
    }

    if (!canMutate) {
        return (
            <span className="soft-info soft-info--normal-size">
                Document ontbreekt.
            </span>
        );
    }

    const [isAdding, setIsAdding] = useState(false);

    const closeModal = () => setIsAdding(false);

    return (
        <React.Fragment>
            {'Document: '}
            <button
                type="button"
                className="btn btn--small"
                onClick={ () => setIsAdding(true) }
            >
                <IconedText icon="attach_file">Toevoegen</IconedText>
            </button>

            <Modal
              isOpen={ isAdding }
              className="modal"
              onRequestClose={ closeModal }
            >
                <button onClick={ closeModal } className="modal__close btn">&times;</button>
                <h1 className="page-title">Document toevoegen</h1>
                <AddDocument zaakUrl={activity.zaak} />
            </Modal>

        </React.Fragment>
    );
};

CaseActivityDocument.propTypes = {
    activity: Activity.isRequired,
    canMutate: PropTypes.bool,
};


export { CaseActivityDocument };
