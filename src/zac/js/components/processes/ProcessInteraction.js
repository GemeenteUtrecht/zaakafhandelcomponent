import React from 'react';
import PropTypes from 'prop-types';

import { TabList, TabContent } from '../Tabs';


const ProcessInteraction = (zaak, endpoint, canDoUserTasks=false, canSendBpmnMessages=false) => {
    return (
        <TabList>

            <TabContent title="Proces 1">
                Tab 1 content
            </TabContent>

            <TabContent title="Proces 2">
                Tab 2 content
            </TabContent>

        </TabList>
    );
};


ProcessInteraction.propTypes = {
    zaak: PropTypes.string.isRequired,
    endpoint: PropTypes.string.isRequired,
    canDoUserTasks: PropTypes.bool,
    canSendBpmnMessages: PropTypes.bool,
};


export { ProcessInteraction };
