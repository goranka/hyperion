module grid_io

  use core_lib
  use type_grid

  implicit none
  save

  private
  public :: grid_exists
  public :: read_grid_3d
  public :: read_grid_4d
  public :: write_grid_3d
  public :: write_grid_4d

  interface read_grid_3d
     module procedure read_grid_3d_sp
     module procedure read_grid_3d_dp
     module procedure read_grid_3d_int
     module procedure read_grid_3d_int8
  end interface read_grid_3d

  interface read_grid_4d
     module procedure read_grid_4d_sp
     module procedure read_grid_4d_dp
     module procedure read_grid_4d_int
     module procedure read_grid_4d_int8
  end interface read_grid_4d

  interface write_grid_3d
     module procedure write_grid_3d_sp
     module procedure write_grid_3d_dp
     module procedure write_grid_3d_int
     module procedure write_grid_3d_int8
  end interface write_grid_3d

  interface write_grid_4d
     module procedure write_grid_4d_sp
     module procedure write_grid_4d_dp
     module procedure write_grid_4d_int
     module procedure write_grid_4d_int8
  end interface write_grid_4d

contains

  logical function grid_exists(group, name)
    implicit none
    integer(hid_t),intent(in) :: group
    character(len=*),intent(in) :: name
    integer(hid_t) :: g_level, g_fab
    if(hdf5_path_exists(group, 'Level 1')) then
       g_level = hdf5_open_group(group, 'Level 1')
       if(hdf5_path_exists(g_level, 'Fab 1')) then
          g_fab = hdf5_open_group(g_level, 'Fab 1')
          if(hdf5_path_exists(g_fab, name)) then
             grid_exists = .true.
          else
             grid_exists = .false.
          end if
       else
          grid_exists = .false.
       end if
    else
       grid_exists = .false.
    end if
  end function grid_exists

  !!@FOR real(sp):sp real(dp):dp integer:int integer(idp):int8

  subroutine read_grid_4d_<T>(group, path, array, geo)

    implicit none

    integer(hid_t), intent(in) :: group
    character(len=*), intent(in) :: path
    @T, intent(out) :: array(:,:)
    type(grid_geometry_desc),intent(in),target :: geo
    @T, allocatable :: array4d(:,:,:,:)
    character(len=100) :: full_path
    integer :: ilevel, ifab
    type(level_desc), pointer :: level
    type(fab_desc), pointer :: fab

    do ilevel=1,size(geo%levels)
       level => geo%levels(ilevel)
       do ifab=1,size(level%fabs)
          fab => level%fabs(ifab)
          write(full_path, '("Level ", I0, "/Fab ", I0,"/")') ilevel, ifab
          full_path = trim(full_path)//trim(path)
          call hdf5_read_array_auto(group, full_path, array4d)
          if(any(is_nan(array4d))) call error("read_grid_4d", "NaN values in 4D array")
          array(fab%start_id:fab%start_id + fab%n_cells - 1, :) = reshape(array4d, (/fab%n_cells, size(array, 2)/))
       end do
    end do

  end subroutine read_grid_4d_<T>

  subroutine read_grid_3d_<T>(group, path, array, geo)

    implicit none

    integer(hid_t), intent(in) :: group
    character(len=*), intent(in) :: path
    @T, intent(out) :: array(:)
    type(grid_geometry_desc),intent(in),target :: geo
    @T, allocatable :: array3d(:,:,:)
    character(len=100) :: full_path
    integer :: ilevel, ifab
    type(level_desc), pointer :: level
    type(fab_desc), pointer :: fab

    do ilevel=1,size(geo%levels)
       level => geo%levels(ilevel)
       do ifab=1,size(level%fabs)
          fab => level%fabs(ifab)
          write(full_path, '("Level ", I0, "/Fab ", I0,"/")') ilevel, ifab
          full_path = trim(full_path)//trim(path)
          call hdf5_read_array_auto(group, full_path, array3d)
          if(any(is_nan(array3d))) call error("read_grid_3d", "NaN values in 3D array")
          array(fab%start_id:fab%start_id + fab%n_cells - 1) = reshape(array3d, (/fab%n_cells/))
       end do
    end do

  end subroutine read_grid_3d_<T>

  subroutine write_grid_4d_<T>(group, path, array, geo) 

    implicit none

    integer(hid_t), intent(in) :: group
    character(len=*), intent(in) :: path
    @T, intent(in) :: array(:,:)
    type(grid_geometry_desc),intent(in) :: geo

  end subroutine write_grid_4d_<T>

  subroutine write_grid_3d_<T>(group, path, array, geo) 

    implicit none

    integer(hid_t), intent(in) :: group
    character(len=*), intent(in) :: path
    @T, intent(in) :: array(:)
    type(grid_geometry_desc),intent(in) :: geo

  end subroutine write_grid_3d_<T>

  !!@END FOR

end module grid_io
