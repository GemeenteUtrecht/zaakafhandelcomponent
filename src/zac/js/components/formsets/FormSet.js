import React, { useState } from 'react';
import PropTypes from 'prop-types';

import { ManagementForm } from './ManagementForm';


const DummyForm = ({ index, data={} }) => {
    return (
        <div>
            Index: {index}
            <br/>
            Data: <pre><code>{JSON.stringify(data)}</code></pre>
        </div>
    );
};


DummyForm.propTypes = {
    index: PropTypes.number.isRequired,
    data: PropTypes.object,
};


const FormSet = ({ configuration, renderForm=DummyForm, formData=[] }) => {
    const existingCount = formData.length;
    const [extra, setExtra] = useState(configuration.extra);
    const forms = formData.map(
        (data, index) => <React.Fragment key={index}>{ renderForm({ index, data: data }) }</React.Fragment>
    );
    const extraForms = Array(extra).fill().map(
        (_, index) => <React.Fragment key={existingCount + index}>{ renderForm({ index: existingCount + index, data: {} }) }</React.Fragment>
    );
    return (
        <React.Fragment>
            <ManagementForm
                prefix={ configuration.prefix }
                initial={ configuration.initial }
                total={ existingCount + extra }
                minNum={ configuration.minNum }
                maxNum={ configuration.maxNum }
            />

            { forms.concat(extraForms) }

        </React.Fragment>
    );
};

FormSet.propTypes = {
    configuration: PropTypes.shape({
        prefix: PropTypes.string.isRequired,
        initial: PropTypes.number.isRequired,
        minNum: PropTypes.number.isRequired,
        maxNum: PropTypes.number.isRequired,
    }).isRequired,
    renderForm: PropTypes.func.isRequired, // a render prop
    formData: PropTypes.arrayOf(PropTypes.object).isRequired,
};


export { FormSet };
