import React from 'react';
import PropTypes from 'prop-types';

import { ManagementForm } from '../formsets/ManagementForm';
import { PrefixContext } from '../formsets/context';


const FormSet = ({ configuration, renderForm, formData=[], emptyFormData=[] }) => {
    const existingCount = formData.length;

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

    const extraForms = emptyFormData.map(
        (data, index) => (
            <PrefixContext.Provider key={existingCount + index} value={getPrefix(existingCount + index)}>
                <RenderForm index={existingCount + index} data={data}/>
            </PrefixContext.Provider>
        )
    );

    const totalForms = formData.length + emptyFormData.length;

    return (
        <React.Fragment>
            <ManagementForm
                prefix={ configuration.prefix }
                initial={ configuration.initial }
                total={ totalForms }
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
        extra: PropTypes.number.isRequired,
        minNum: PropTypes.number.isRequired,
        maxNum: PropTypes.number.isRequired,
    }).isRequired,
    renderForm: PropTypes.func.isRequired, // a render prop
    formData: PropTypes.arrayOf(PropTypes.object).isRequired,
    emptyFormData: PropTypes.arrayOf(PropTypes.object),
};


export { FormSet };
