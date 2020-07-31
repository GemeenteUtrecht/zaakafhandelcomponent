import React from 'react';
import PropTypes from 'prop-types';


const ProcessInteraction = (zaak, endpoint, canDoUserTasks=false, canSendBpmnMessages=false) => {
    return null;
};


ProcessInteraction.propTypes = {
    zaak: PropTypes.string.isRequired,
    endpoint: PropTypes.string.isRequired,
    canDoUserTasks: PropTypes.bool,
    canSendBpmnMessages: PropTypes.bool,
};


export { ProcessInteraction };
