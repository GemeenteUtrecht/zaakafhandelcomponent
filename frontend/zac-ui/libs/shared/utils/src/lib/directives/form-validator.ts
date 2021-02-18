import { FormArray, FormControl, ValidatorFn } from '@angular/forms';

export function atleastOneValidator(): ValidatorFn {
  return (control: FormArray) => {
    if (control.value.find(x => x))
      return null
    return { "error": "Minimaal één selectie benodigd." }
  }
}

export function childValidator(): ValidatorFn {
  return (control: FormArray) => {
    console.log(control);
    if (control.value.status === "VALID")
      return null
    return { "error": "Dit veld is verplicht." }
  }
}
