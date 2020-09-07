import React, { useState } from 'react';
import PropTypes from 'prop-types';

import { ManagementForm } from './ManagementForm';
import { AddForm } from './AddForm';
import { PrefixContext } from './context';


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


const FormSet = ({ configuration, renderForm=DummyForm, renderAdd=AddForm, formData=[] }) => {
    const existingCount = formData.length;
    const [extra, setExtra] = useState(configuration.extra);

    const RenderForm = renderForm;

    const getPrefix = (index) => {
        return `${configuration.prefix}-${index}`;
    };

    const forms = formData.map(
        (data, index) => (
            <PrefixContext.Provider key={index} value={ getPrefix(index) }>
                <RenderForm index={index} data={data} />
            </PrefixContext.Provider>
        )
    );
    const extraForms = Array(extra).fill().map(
        (_, index) => (
            <PrefixContext.Provider key={existingCount + index} value={ getPrefix(existingCount + index) }>
                <RenderForm index={existingCount + index} data={ {} } />
            </PrefixContext.Provider>
        )
    );

    const onAdd = (event) => {
        event.preventDefault();
        setExtra(extra + 1);
    };

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

            { renderAdd({ onAdd }) }

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
    renderAdd: PropTypes.func, // a render prop
    formData: PropTypes.arrayOf(PropTypes.object).isRequired,
};


export { FormSet };
