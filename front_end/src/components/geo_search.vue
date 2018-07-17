<template>

  <section id="geo_search">
    <div class="geo_search--input_wrapper">
      <input
        class="geo_search--input"
        :class="{ working : inProgress }"
        v-model="searchText"
        :placeholder="label"
      >
      <button @click="clearSearch" class="geo_search--clear" v-show="readyToSearch">X</button>
      <p class="geo_search--message" v-show="showMessage">{{ message }}</p>
    </div>

    <h3 v-show="searchResultCount">{{ searchResultCount }} Results found for <strong>" {{ searchText }} "</strong></h3>

    <section class="geo_search--results">
      <article
        v-for="(geo, index) in geos"
        v-if="geo.data"
        :key="index"
        class="geo_search--result"
      >
        <v-map :zoom="zoom" :center="geo.data.location" :zoomControl="false" >
          <v-tilelayer url="http://{s}.tile.osm.org/{z}/{x}/{y}.png"></v-tilelayer>
          <v-marker :lat-lng="geo.data.location"></v-marker>
        </v-map>

        <div class="geo_search--result_info">
          <h2>{{ geo.display }}</h2>
          <p v-if="geo.data"><strong>POP:</strong> {{ numberWithCommas(geo.data.total_pop) }}</p>
        </div>
      </article>
    </section>
  </section>
</template>

<script>
import axios from 'axios'
import _ from 'lodash'

export default {
  name: 'geoSearch',
  data () {
    return {
      label: 'Find a Way to Contribute from Wherever You Are',
      searchText: null,
      inProgress: false,
      geos: [],
      zoom: 8,
      message: 'We couldn\'t find any results for your search, sorry. Try a different place.'
    }
  },
  watch: {
    searchText () {
      if (this.readyToSearch) {
        this.searchGeoService(this.searchText)
      }
    }
  },
  methods: {
    searchGeoService: _.debounce(function (term) {
      let vue = this
      this.inProgress = true
      this.geos = {}
      axios.get(this.dataSource)
        .then(function (response) {
          let data = response.data || {}
          vue.geos = data
          vue.inProgress = false
        })
        .catch(function (error) {
          console.log(`UH OH ======== :( ${error}`)
          vue.inProgress = false
        })
    }, 400),
    numberWithCommas (num) {
      return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',')
    },
    clearSearch () {
      this.inProgress = false
      this.searchText = ''
      this.geos = {}
    }
  },
  computed: {
    readyToSearch () {
      return this.searchText && this.searchText.length > 2
    },
    dataSource () {
      return `http://0.0.0.0:5000/geos/?match_string=${this.searchText}&match_limit=-1`
    },
    searchResultCount () {
      let resultsFound = this.geos && _.keys(this.geos).length > 0
      return resultsFound ? _.keys(this.geos).length : 0
    },
    showMessage () {
      return false
    }
  }
}
</script>

<style lang="scss" scoped >
@import '~@/sass/palette.scss';
@import '~@/sass/animate.scss';

#geo_search {

  * {
    transition: all .2s;
  }

  .geo_search--input {
    width: 100%;
    padding: 1rem;
    margin: 1rem 0;
    background: white;
    border: none;
    font-size: 1.5rem;
    font-weight: 700;
    color: $aqua;
    text-align: center;

    &.working {
      animation: activePulse 2s infinite;
    }
  }

  .geo_search--input_wrapper {
    position: relative;
  }

  $clear_dimension: 2em;

  .geo_search--clear {
    position: absolute;
    right: 1rem;
    top: 1.5rem;
    font-size: 1.25rem;
    opacity: .75;
    color: white;
    height: $clear_dimension;
    width: $clear_dimension;
    border-radius: 50%;
    background: $light_blue;

    &:hover {
      cursor: pointer;
      opacity: 1;
    }
  }

  .geo_search--results {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
  }

  .geo_search--result {
    @include fadeInUp();
    background: white;
    border-bottom: 4px solid;
    border-color: $light_blue;
    text-align: left;
    width: 28%;
    margin-bottom: .5rem;

    &:hover {
      cursor: pointer;
    }

    .leaflet-container {
      height: 10em;
    }
  }

  .geo_search--result_info {
    padding: .5rem;
  }
}

</style>
