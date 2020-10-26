import React from 'react';
import PropTypes from 'prop-types';

import { ManagementForm } from '../formsets/ManagementForm';
import { PrefixContext } from '../formsets/context';


const FormSet = ({ configuration, renderForm, deleteForm, formData=[], emptyFormData=[], dataToDelete=[] }) => {

    const RenderForm = renderForm;
    const DeleteForm = deleteForm;

    const getPrefix = (index) => {
        return `${configuration.prefix}-${index}`;
    };

    const formsAndEmptyForms = formData.concat(emptyFormData);

    const forms = formsAndEmptyForms.map(
        (data, index) => (
            <PrefixContext.Provider key={index} value={ getPrefix(index) }>
                <RenderForm index={index} data={data} />
            </PrefixContext.Provider>
        )
    );

    const renderDataToDelete = () => {
        const formsForDeletingData = dataToDelete.map(
            (data, index) => (
                <PrefixContext.Provider
                    key={formsAndEmptyForms.length + index}
                    value={getPrefix(formsAndEmptyForms.length + index)}
                >
                    <DeleteForm index={formsAndEmptyForms.length + index} data={data}/>
                </PrefixContext.Provider>
            )
        );

        if (formsForDeletingData.length > 0) {
            return (
                <React.Fragment>
                    <h4>De volgende toestemmingen worden verwijderd</h4>
                    <ul>
                        {formsForDeletingData}
                    </ul>
                </React.Fragment>
            );
        }
    };

    const totalForms = formsAndEmptyForms.length + dataToDelete.length;

    return (
        <React.Fragment>
            <ManagementForm
                prefix={ configuration.prefix }
                initial={ configuration.initial }
                total={ totalForms }
                minNum={ configuration.minNum }
                maxNum={ configuration.maxNum }
            />

            { forms }
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
