import React from 'react';
import ReactDOM from 'react-dom';

import './fetch-zaakobjecten';
import './fetch-tasks';
import './fetch-messages';
import { ReviewRequestTable } from "./ReviewRequest";
import { jsonScriptToVar } from '../../utils/json-script';


const init = () => {
    const node = document.getElementById('review-requests-react');
    if (!node) {
        return;
    }

    const reviewRequests = jsonScriptToVar('reviewRequests');

    ReactDOM.render(
        <ReviewRequestTable reviewRequests={reviewRequests}/>,
        node
    );
};


init();
