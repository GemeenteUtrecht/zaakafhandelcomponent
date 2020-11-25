import React, { useState } from 'react';
import PropTypes from 'prop-types';

import { ManagementForm } from './ManagementForm';
import { AddForm } from './AddForm';
import { PrefixContext } from './context';

const DummyForm = ({ index, data = {} }) => (
    <div>
        Index:
        {' '}
        {index}
        <br />
        Data:
        {' '}
        <pre><code>{JSON.stringify(data)}</code></pre>
    </div>
);

DummyForm.propTypes = {
    index: PropTypes.number.isRequired,
    data: PropTypes.object,
};

const FormSet = ({
    configuration,
    renderForm = DummyForm,
    renderAdd = AddForm,
    formData = [],
    formsContainer=React.Fragment,
}) => {
    const existingCount = formData.length;
    const [extra, setExtra] = useState(configuration.extra);

    const onDelete = (event) => {
        event.preventDefault();
        setExtra(extra - 1);
    };

    const RenderForm = renderForm;
    const Container = formsContainer;

    const getPrefix = (index) => `${configuration.prefix}-${index}`;

    const forms = formData.map(
        (data, index) => (
            <PrefixContext.Provider key={index} value={getPrefix(index)}>
                <RenderForm index={index} totalStepsIndex={extra} data={data} onDelete={onDelete} />
            </PrefixContext.Provider>
        ),
    );
    const extraForms = Array(extra).fill().map(
        (_, index) => (
            <PrefixContext.Provider key={existingCount + index} value={getPrefix(existingCount + index)}>
                <RenderForm index={existingCount + index} totalStepsIndex={extra} data={{}} onDelete={onDelete} />
            </PrefixContext.Provider>
        ),
    );

    const onAdd = (event) => {
        event.preventDefault();
        setExtra(extra + 1);
    };

    return (
        <>
            <ManagementForm
                prefix={configuration.prefix}
                initial={configuration.initial}
                total={existingCount + extra}
                minNum={configuration.minNum}
                maxNum={configuration.maxNum}
            />

            <Container>{ forms.concat(extraForms) }</Container>

            { renderAdd ? renderAdd({ onAdd }) : null }

        </>
    );
};

FormSet.propTypes = {
    configuration: PropTypes.shape({
        prefix: PropTypes.string.isRequired,
        initial: PropTypes.number.isRequired,
        extra: PropTypes.number.isRequired,
        minNum: PropTypes.number.isRequired,
        maxNum: PropTypes.number.isRequired,
    }).isRequired,
    renderForm: PropTypes.func.isRequired, // a render prop
    renderAdd: PropTypes.func, // a render prop
    formData: PropTypes.arrayOf(PropTypes.object).isRequired,
};

export { FormSet };
