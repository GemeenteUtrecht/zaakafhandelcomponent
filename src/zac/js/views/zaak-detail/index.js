import React from 'react';
import ReactDOM from 'react-dom';
import Modal from "react-modal";

import './fetch-zaakobjecten';
import { ReviewRequestTable } from "../../components/review-requests";
import { DownloadUrlContext } from "../../components/documents/context";
import { jsonScriptToVar } from '../../utils/json-script';


const init = () => {
    const node = document.getElementById('review-requests-react');
    if (!node) {
        return;
    }

    Modal.setAppElement(node);

    const reviewRequests = jsonScriptToVar('reviewRequests');
    const { downloadUrl } = node.dataset;

    ReactDOM.render(
        <DownloadUrlContext.Provider value={downloadUrl}>
            <ReviewRequestTable reviewRequests={reviewRequests}/>
        </DownloadUrlContext.Provider>,
        node
    );
};


init();
