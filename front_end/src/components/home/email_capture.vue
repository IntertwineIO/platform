<template>
  <section>
    <div class="intertwine__email_capture">
      <input v-model="email_address" :placeholder="label">
      <button v-if="emailValid" @click="submitEmail(email_address)">Submit</button>
      <button class="disabled" v-if="!emailValid" @click="shootBlank" disabled>Your email?</button>
    </div>
    <p class="intertwine__email_capture--message" v-show="showMessage">{{ message }}</p>
  </section>
</template>

<script>
export default {
  name: 'EmailCapture',
  data () {
    return {
      label: 'Enter your email address to chart our progress...',
      email_address: null,
      message: 'The email address you submitted is not the correct format. Please adjust so we can keep in touch.'
    }
  },
  methods: {
    submitEmail (emailAddress) {
      console.log(`Submit this email >>>>> ${emailAddress}`)
    },
    shootBlank () {
      return true
    }
  },
  computed: {
    emailExists () {
      return !!(this.email_address)
    },
    emailIsLong () {
      return this.emailExists ? this.email_address.length > 6 : false
    },
    emailValid () {
      // eslint-disable-next-line
      var re = /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/
      return this.emailExists ? re.test(this.email_address) : false
    },
    showMessage () {
      return (this.emailIsLong && !this.emailValid)
    }
  }
}
</script>

<style lang="scss" scoped >
@import '~@/sass/palette.scss';
.intertwine__email_capture {
  display: flex;
  padding: 0 2rem;
  input {
    padding: 1rem;
    width: 65%;
    border: none;
    background: white;
    font-size: 1rem;
  }
  button {
    padding: 0 5rem;
    font-size: 1rem;
    background-color: $aqua;
    color: white;
    border: none;
  }
  .disabled {
    background-color: rgba(2,200,167,.5);
  }
}

</style>
