import React from 'react';
import ReactDOM from 'react-dom';
import Modal from 'react-modal';

import './fetch-zaakobjecten';
import { CsrfTokenContext } from '../../components/forms/context';
import { ReviewRequestTable } from '../../components/review-requests';
import { DownloadUrlContext } from '../../components/documents/context';
import { jsonScriptToVar } from '../../utils/json-script';
import { AddZaakDocument } from './AddZaakDocument';
import BetrokkenenTable from '../../components/betrokkenen/Betrokkenen';
import {AddZaakRelation} from './AddZaakRelation';


const initReviewRequests = () => {
    const node = document.getElementById('review-requests-react');
    if (!node) {
        return;
    }

    Modal.setAppElement(node);

    const reviewRequests = jsonScriptToVar('reviewRequests');
    const { downloadUrl } = node.dataset;

    ReactDOM.render(
        <DownloadUrlContext.Provider value={downloadUrl}>
            <ReviewRequestTable reviewRequests={reviewRequests} />
        </DownloadUrlContext.Provider>,
        node,
    );
};

const initDocuments = () => {
    const node = document.getElementById('add-document-react');
    if (!node) {
        return;
    }
    const { zaak, csrftoken } = node.dataset;

    Modal.setAppElement(node);

    ReactDOM.render(
        <CsrfTokenContext.Provider value={csrftoken}>
            {/* TODO: properly insert document row instead of full page refresh */}
            <AddZaakDocument zaakUrl={zaak} onUploadComplete={() => window.location.reload()} />
        </CsrfTokenContext.Provider>,
        node,
    );
};

const initBetrokkenenTable = () => {
    const node = document.getElementById('betrokkenen-react');
    if (!node) {
        return;
    }

    const { csrftoken } = node.dataset;

    const dataNodes = document.querySelectorAll('.betrokkene-data');

    ReactDOM.render(
        <CsrfTokenContext.Provider value={csrftoken}>
            <BetrokkenenTable betrokkeneNodes={dataNodes} />
        </CsrfTokenContext.Provider>,
        node,
    );
};

const initZakenRelations = () => {
    const node = document.getElementById('add-zaken-relation');
    if (!node) {
        return;
    }

    const { zaak, csrftoken } = node.dataset;

    Modal.setAppElement(node);

    ReactDOM.render(
        <AddZaakRelation zaakUrl={zaak} csrfToken={csrftoken} onSuccessfulSubmit={() => window.location.reload()} />,
        node,
    );
};

const init = () => {
    initReviewRequests();
    initDocuments();
    initBetrokkenenTable();
    initZakenRelations();
};

init();
