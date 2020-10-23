import React from 'react';
import PropTypes from 'prop-types';

import { ManagementForm } from '../formsets/ManagementForm';
import { PrefixContext } from '../formsets/context';


const FormSet = ({ configuration, renderForm, formData=[], emptyFormData=[], dataToDelete=[] }) => {

    const RenderForm = renderForm;

    const getPrefix = (index) => {
        return `${configuration.prefix}-${index}`;
    };

    // TODO: Concatenate these arrays and then make forms out of them
    const forms = formData.map(
        (data, index) => (
            <PrefixContext.Provider key={index} value={ getPrefix(index) }>
                <RenderForm index={index} data={data} />
            </PrefixContext.Provider>
        )
    );

    const extraForms = emptyFormData.map(
        (data, index) => (
            <PrefixContext.Provider key={formData.length + index} value={getPrefix(formData.length + index)}>
                <RenderForm index={formData.length + index} data={data}/>
            </PrefixContext.Provider>
        )
    );

    const renderDataToDelete = () => {
        const formsForDeletingData = dataToDelete.map(
            (data, index) => (
                <PrefixContext.Provider
                    key={formData.length + emptyFormData.length + index}
                    value={getPrefix(formData.length + emptyFormData.length + index)}
                >
                    <RenderForm index={formData.length + emptyFormData.length + index} data={data}/>
                </PrefixContext.Provider>
            )
        );

        if (formsForDeletingData.length > 0) {
            return (
                <React.Fragment>
                    <h4>The following permissions will be deleted</h4>
                    {formsForDeletingData}
                </React.Fragment>
            );
        }
    };

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
            {renderDataToDelete()}
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
